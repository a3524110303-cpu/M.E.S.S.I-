"""Revisión y alta atómica de cuentas e inscripciones por lote."""
import secrets

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from . import organization
from .models import AuditEvent, CourseGroup, Enrollment, Student
from .services import _require

LIMIT = 1000


def prepare(actor, records, group_ids):
    _require(actor, "admin")
    ids = sorted({organization._identifier(value) for value in group_ids})
    if not ids or len(ids) > 30:
        raise ValidationError("Selecciona entre 1 y 30 grupos y materias.")
    groups = list(CourseGroup.objects.filter(pk__in=ids, period__is_open=True))
    if len(groups) != len(ids):
        raise ValidationError("Algún grupo ya no existe o su periodo está cerrado.")
    if not isinstance(records, list) or not 1 <= len(records) <= LIMIT:
        raise ValidationError("Incluye entre 1 y 1000 alumnos por archivo.")
    for number, raw in enumerate(records, 2):
        if not isinstance(raw, dict) or not all(isinstance(raw.get(field, ""), str) for field in ("codigo", "nombres", "apellidos", "usuario")):
            raise ValidationError(f"Fila {number}: los datos deben ser texto.")
    codes = set(Student.objects.values_list("code", flat=True))
    requested = {row.get("codigo", "").strip().upper() for row in records}
    students = {item.code: item for item in Student.objects.select_related("user__profile").filter(code__in=requested)}
    # Reserva también los códigos explícitos del archivo antes de generar otros.
    reserved = codes | {row.get("codigo", "").strip().upper() for row in records}
    next_code = max((int(code[4:]) for code in codes), default=0) + 1
    used_codes, used_users, result = set(), set(), []
    for number, raw in enumerate(records, 2):
        row = {field: raw.get(field, "").strip() for field in ("codigo", "nombres", "apellidos", "usuario")}
        row["codigo"] = row["codigo"].upper()
        if not row["codigo"]:
            while f"EST-{next_code:03d}" in reserved:
                next_code += 1
            row["codigo"] = f"EST-{next_code:03d}"
            reserved.add(row["codigo"])
            next_code += 1
        try:
            Student._meta.get_field("code").clean(row["codigo"], None)
        except ValidationError as exc:
            raise ValidationError([f"Fila {number}: {message}" for message in exc.messages]) from exc
        if row["codigo"] in used_codes:
            raise ValidationError(f"Fila {number}: código repetido {row['codigo']}. Usa una fila por alumno.")
        used_codes.add(row["codigo"])
        existing = students.get(row["codigo"])
        if existing:
            account = existing.user
            if not account.is_active or not hasattr(account, "profile") or account.profile.role != "estudiante":
                raise ValidationError(f"Fila {number}: {row['codigo']} no tiene una cuenta activa de estudiante.")
            for field, current in (("nombres", account.first_name), ("apellidos", account.last_name), ("usuario", account.username)):
                if row[field] and row[field] != current:
                    raise ValidationError(f"Fila {number}: {field} no coincide con la cuenta de {row['codigo']}.")
                row[field] = current
            row["student_id"] = existing.pk
        else:
            if not row["nombres"] or not row["apellidos"]:
                raise ValidationError(f"Fila {number}: completa nombres y apellidos para el alumno nuevo.")
            row["usuario"] = row["usuario"] or "alumno." + row["codigo"].lower()
            account = get_user_model()(username=row["usuario"], first_name=row["nombres"], last_name=row["apellidos"])
            try:
                account.clean_fields(exclude=["password"])
            except ValidationError as exc:
                raise ValidationError([f"Fila {number}: {message}" for message in exc.messages]) from exc
            row["student_id"] = None
        folded = row["usuario"].casefold()
        if folded in used_users:
            raise ValidationError(f"Fila {number}: usuario repetido {row['usuario']}.")
        used_users.add(folded)
        result.append(row)
    # Una sola consulta para usuarios existentes; la base también aplica su unicidad al guardar.
    existing_users = {name.casefold() for name in get_user_model().objects.filter(username__in=[r["usuario"] for r in result]).values_list("username", flat=True)}
    for row in result:
        if row["student_id"] is None and row["usuario"].casefold() in existing_users:
            raise ValidationError(f"El usuario {row['usuario']} ya existe. Usa su código EST- si es un alumno existente, o elige otro usuario.")
    already = set(Enrollment.objects.filter(group_id__in=ids, student_id__in=[r["student_id"] for r in result if r["student_id"]]).values_list("student_id", "group_id"))
    return {"rows": result, "group_ids": ids, "new_accounts": sum(r["student_id"] is None for r in result),
            "new_enrollments": len(result) * len(ids) - len(already), "skipped": len(already)}


def commit(actor, preview):
    _require(actor, "admin")
    try:
        with transaction.atomic():
            # Orden estable y mismos padres que las operaciones individuales.
            list(Student.objects.select_for_update().filter(pk__in=[r["student_id"] for r in preview["rows"] if r["student_id"]]).order_by("pk"))
            list(CourseGroup.objects.select_for_update().filter(pk__in=preview["group_ids"]).order_by("pk"))
            current = prepare(actor, preview["rows"], preview["group_ids"])
            if current != preview:
                raise ValidationError("Los datos cambiaron desde la revisión. Revisa nuevamente el archivo antes de guardar.")
            credentials, student_ids = [], []
            for row in current["rows"]:
                student_id = row["student_id"]
                if student_id is None:
                    password = secrets.token_urlsafe(18)
                    account = organization.create_account(actor, row["usuario"], password, row["nombres"], row["apellidos"], "estudiante", row["codigo"])
                    student_id = account.student.pk
                    credentials.append({**{field: row[field] for field in ("codigo", "nombres", "apellidos", "usuario")}, "clave": password})
                student_ids.append(student_id)
            existing = set(Enrollment.objects.filter(student_id__in=student_ids, group_id__in=current["group_ids"]).values_list("student_id", "group_id"))
            enrollments = [Enrollment(student_id=student_id, group_id=group_id)
                           for student_id in student_ids for group_id in current["group_ids"]
                           if (student_id, group_id) not in existing]
            Enrollment.objects.bulk_create(enrollments, batch_size=500)
            # Consultar los IDs funciona también en MySQL, donde bulk_create no los devuelve.
            saved = Enrollment.objects.filter(student_id__in=student_ids, group_id__in=current["group_ids"])
            AuditEvent.objects.bulk_create([
                AuditEvent(author=actor, action="inscribir_estudiante", entity="enrollment", entity_id=item.pk)
                for item in saved if (item.student_id, item.group_id) not in existing
            ], batch_size=500)
            return {"credentials": credentials, "enrolled": len(enrollments), "skipped": current["skipped"]}
    except IntegrityError as exc:
        raise ValidationError("Se encontró un registro duplicado mientras se guardaba. No se guardó el lote; revisa el archivo de nuevo.") from exc
