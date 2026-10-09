"""Operaciones autorizadas y transaccionales del portal compartido."""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Exists, OuterRef

from messi.data import validate_records, ValidationError as DataError
from messi.model import ModelUnavailable, _read_metadata, score_records
from .models import (
    AuditEvent, CourseGroup, Enrollment, FollowUp, HelpRequest, Indicator,
    Period, Prediction, Profile, Student, SupportCase, TutorAssignment,
)


class ConflictError(ValidationError):
    """La versión del formulario ya no coincide con el registro compartido."""


def role_for(user):
    if not user.is_authenticated or not user.is_active:
        return None
    if user.is_superuser:
        return "admin"
    return Profile.objects.filter(user=user).values_list("role", flat=True).first()


def _require(user, role):
    if role_for(user) != role:
        raise PermissionDenied("Tu cuenta no tiene permiso para realizar esta acción.")


def _tutor_scope(queryset, user, student_field, period_field):
    assigned = TutorAssignment.objects.filter(
        tutor=user, student_id=OuterRef(student_field), period_id=OuterRef(period_field),
    )
    return queryset.filter(Exists(assigned))


def visible_groups(user):
    qs = CourseGroup.objects.select_related("period")
    role = role_for(user)
    if role == "docente":
        return qs.filter(teachers=user).distinct()
    if role == "estudiante":
        return qs.filter(enrollments__student__user=user).distinct()
    if role == "tutor":
        allowed = _tutor_scope(Enrollment.objects.all(), user, "student_id", "group__period_id")
        return qs.filter(enrollments__in=allowed).distinct()
    return qs.none()


def visible_students(user):
    qs = Student.objects.select_related("user")
    role = role_for(user)
    if role == "docente":
        return qs.filter(enrollments__group__teachers=user).distinct()
    if role == "estudiante":
        return qs.filter(user=user)
    if role == "tutor":
        return qs.filter(tutor_assignments__tutor=user).distinct()
    return qs.none()


def visible_enrollments(user):
    qs = Enrollment.objects.select_related("student__user", "group__period")
    role = role_for(user)
    if role == "docente":
        return qs.filter(group__teachers=user).distinct()
    if role == "estudiante":
        return qs.filter(student__user=user)
    if role == "tutor":
        return _tutor_scope(qs, user, "student_id", "group__period_id")
    return qs.none()


def teacher_enrollments(user, group_id):
    _require(user, "docente")
    if not visible_groups(user).filter(pk=group_id).exists():
        raise PermissionDenied("El grupo no está asignado a tu cuenta.")
    return visible_enrollments(user).filter(group_id=group_id).order_by("student__code")


def visible_indicators(user):
    return Indicator.objects.filter(enrollment__in=visible_enrollments(user)).select_related(
        "enrollment__student__user", "enrollment__group__period", "updated_by",
    )


def visible_predictions(user):
    return Prediction.objects.filter(indicator__in=visible_indicators(user)).select_related(
        "indicator__enrollment__student__user", "indicator__enrollment__group__period",
    )


def visible_requests(user):
    qs = HelpRequest.objects.select_related("student__user", "period")
    role = role_for(user)
    if role == "estudiante":
        return qs.filter(student__user=user)
    if role == "tutor":
        return _tutor_scope(qs, user, "student_id", "period_id")
    return qs.none()


def visible_cases(user):
    qs = SupportCase.objects.select_related("student__user", "period", "tutor", "request", "prediction")
    role = role_for(user)
    if role == "estudiante":
        return qs.filter(student__user=user)
    if role == "tutor":
        return _tutor_scope(qs.filter(tutor=user), user, "student_id", "period_id")
    return qs.none()


def _text(value, label, optional=False):
    if not isinstance(value, str) or len(value.strip()) > 1000 or (not optional and not value.strip()):
        raise ValidationError(f"{label}: escribe entre 1 y 1000 caracteres." if not optional else f"{label}: máximo 1000 caracteres.")
    return value.strip()


def _version(value):
    if isinstance(value, bool):
        raise ValidationError("La versión del registro es inválida.")
    try:
        result = int(value)
        if str(result) != str(value) or result < 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValidationError("La versión del registro es inválida.")
    return result


def _audit(user, action, obj):
    AuditEvent.objects.create(author=user, action=action, entity=obj._meta.model_name, entity_id=obj.pk)


def _locked_enrollment(user, enrollment_id):
    # Bloquear el padre serializa también la creación del primer indicador.
    if not visible_enrollments(user).filter(pk=enrollment_id).exists():
        raise PermissionDenied("La inscripción no está asignada a tu cuenta.")
    enrollment = Enrollment.objects.select_for_update().get(pk=enrollment_id)
    if not enrollment.group.period.is_open:
        raise ValidationError("La captura de este periodo está cerrada.")
    return enrollment


def _save_indicator(user, enrollment, cut, grade, attendance, homework, expected_version):
    expected = _version(expected_version)
    obj = Indicator.objects.select_for_update().filter(enrollment=enrollment, cut=cut).first()
    if expected != (obj.version if obj else 0):
        raise ConflictError("Los indicadores cambiaron desde que abriste el formulario. Recarga y revisa los datos.")
    if obj is None:
        obj = Indicator(enrollment=enrollment, cut=cut, updated_by=user)
    values = {}
    for key, raw in (("grade", grade), ("attendance", attendance), ("homework", homework)):
        try:
            value = Decimal(str(raw))
            if not value.is_finite():
                raise ValueError
            values[key] = value
        except (ValueError, ArithmeticError):
            raise ValidationError("Los indicadores deben ser números finitos.")
    changed = obj.pk is None or any(getattr(obj, key) != value for key, value in values.items())
    if not changed:
        return obj
    if obj.pk:
        obj.version += 1
    for key, value in values.items():
        setattr(obj, key, value)
    obj.updated_by = user
    obj.full_clean()
    obj.save()
    _audit(user, "guardar_indicadores", obj)
    return obj


@transaction.atomic
def save_indicator(user, enrollment_id, cut, grade, attendance, homework, expected_version):
    _require(user, "docente")
    enrollment = _locked_enrollment(user, enrollment_id)
    return _save_indicator(user, enrollment, cut, grade, attendance, homework, expected_version)


@transaction.atomic
def import_indicators(user, group_id, cut, records, expected_versions):
    _require(user, "docente")
    allowed = {row.student.code: row for row in teacher_enrollments(user, group_id)}
    try:
        clean = validate_records(records)
    except DataError as exc:
        raise ValidationError(str(exc)) from exc
    if not isinstance(expected_versions, dict):
        raise ValidationError("Falta la versión del formulario de importación.")
    versions = {str(key): value for key, value in expected_versions.items()}
    if set(versions) - {str(row.pk) for row in allowed.values()}:
        raise PermissionDenied("La versión de importación incluye inscripciones ajenas al grupo.")
    for row in clean:
        if row["id_estudiante"] not in allowed:
            raise PermissionDenied("El archivo contiene estudiantes que no están inscritos en tu grupo.")
    result = []
    # Orden estable de bloqueo para las importaciones concurrentes.
    ordered = sorted(clean, key=lambda row: allowed[row["id_estudiante"]].pk)
    for row in ordered:
        enrollment = _locked_enrollment(user, allowed[row["id_estudiante"]].pk)
        result.append(_save_indicator(user, enrollment, cut,
            row["nota_parcial"], row["asistencia"], row["tareas_entregadas"],
            versions.get(str(enrollment.pk), 0)))
    return result


def calculate_risk(user, indicator_id, expected_version):
    _require(user, "docente")
    expected = _version(expected_version)
    obj = visible_indicators(user).filter(pk=indicator_id).first()
    if obj is None:
        raise PermissionDenied("No tienes acceso a estos indicadores.")
    if obj.version != expected:
        raise ConflictError("Los indicadores cambiaron. Recarga antes de calcular.")
    if obj.cut != "primer_parcial":
        raise ValidationError("Este modelo demostrativo sólo admite indicadores del primer parcial.")
    model_path = settings.MESSI_MODEL_PATH
    _, metadata = _read_metadata(model_path)
    scored = score_records([{
        "id_estudiante": obj.enrollment.student.code, "nota_parcial": float(obj.grade),
        "asistencia": float(obj.attendance), "tareas_entregadas": float(obj.homework),
    }], model_path)[0]
    _, after = _read_metadata(model_path)
    if after["model_sha256"] != metadata["model_sha256"]:
        raise ModelUnavailable("El modelo cambió durante el cálculo. Vuelve a intentarlo.")
    with transaction.atomic():
        _locked_enrollment(user, obj.enrollment_id)
        locked = Indicator.objects.select_for_update().get(pk=obj.pk)
        if locked.version != expected:
            raise ConflictError("Los indicadores cambiaron durante el cálculo. Recarga y vuelve a calcular.")
        prediction, created = Prediction.objects.get_or_create(
            indicator=locked, indicator_version=locked.version, model_version=metadata["model_sha256"],
            defaults={"grade": locked.grade, "attendance": locked.attendance, "homework": locked.homework,
                "score": scored["puntuacion_riesgo"], "threshold": metadata["threshold"], "alert": scored["alerta"]},
        )
        if created:
            prediction.full_clean()
            _audit(user, "calcular_riesgo_demo", prediction)
        return prediction


@transaction.atomic
def create_request(user, period_id, message):
    _require(user, "estudiante")
    student = Student.objects.filter(user=user).first()
    if student is None or not Enrollment.objects.filter(student=student, group__period_id=period_id).exists():
        raise PermissionDenied("Tu cuenta no está inscrita en el periodo indicado.")
    if not Period.objects.filter(pk=period_id, is_open=True).exists():
        raise ValidationError("El periodo está cerrado para nuevas solicitudes.")
    obj = HelpRequest(student=student, period_id=period_id, message=_text(message, "Solicitud"))
    obj.full_clean()
    obj.save()
    _audit(user, "enviar_solicitud", obj)
    return obj


def _assigned_tutor(user, student_id, period_id):
    _require(user, "tutor")
    assignment = TutorAssignment.objects.select_for_update().filter(
        tutor=user, student_id=student_id, period_id=period_id,
    ).first()
    if assignment is None:
        raise PermissionDenied("No estás asignado a este estudiante en el periodo indicado.")
    return assignment


@transaction.atomic
def create_case(user, student_id, period_id, agreement, internal_notes="", request_id=None, prediction_id=None):
    _assigned_tutor(user, student_id, period_id)
    if not Period.objects.filter(pk=period_id, is_open=True).exists():
        raise ValidationError("El periodo está cerrado para nuevos casos.")
    request = None
    prediction = None
    if request_id:
        request = HelpRequest.objects.select_for_update().filter(pk=request_id, student_id=student_id, period_id=period_id).first()
        if request is None:
            raise PermissionDenied("La solicitud no corresponde a este estudiante y periodo.")
        if SupportCase.objects.filter(request=request).exists():
            raise ConflictError("Esta solicitud ya tiene un caso de apoyo.")
    if prediction_id:
        candidate = Prediction.objects.filter(
            pk=prediction_id, indicator__enrollment__student_id=student_id,
            indicator__enrollment__group__period_id=period_id,
        ).first()
        if candidate is None:
            raise PermissionDenied("La predicción no corresponde a este estudiante y periodo.")
        # Mismo orden que captura e inferencia: inscripción → indicador →
        # predicción. Un JOIN con FOR UPDATE puede invertir ese orden en MySQL.
        _locked_enrollment(user, candidate.indicator.enrollment_id)
        indicator = Indicator.objects.select_for_update().get(pk=candidate.indicator_id)
        prediction = Prediction.objects.select_for_update().get(pk=candidate.pk)
        prediction.indicator = indicator
        if not prediction.alert or not prediction.is_current:
            raise ValidationError("Selecciona una alerta vigente para abrir el caso.")
        if SupportCase.objects.filter(prediction=prediction).exists():
            raise ConflictError("Esta alerta ya tiene un caso de apoyo.")
    obj = SupportCase(student_id=student_id, period_id=period_id, tutor=user,
        request=request, prediction=prediction, agreement=_text(agreement, "Acuerdo"),
        internal_notes=_text(internal_notes, "Nota interna", optional=True))
    obj.full_clean()
    obj.save()
    if request:
        request.status = "Atendida"
        request.save(update_fields=["status"])
    _audit(user, "registrar_apoyo", obj)
    return obj


@transaction.atomic
def add_followup(user, case_id, notes, internal_notes, status, expected_version):
    _require(user, "tutor")
    obj = visible_cases(user).filter(pk=case_id).first()
    if obj is None:
        raise PermissionDenied("No tienes acceso a este caso.")
    _assigned_tutor(user, obj.student_id, obj.period_id)
    obj = SupportCase.objects.select_for_update().get(pk=case_id)
    if obj.version != _version(expected_version):
        raise ConflictError("El caso cambió desde que abriste el formulario. Recarga para revisar el seguimiento.")
    if status not in dict(SupportCase.STATUSES):
        raise ValidationError("Selecciona un estado válido.")
    followup = FollowUp(case=obj, author=user, notes=_text(notes, "Avance"),
        internal_notes=_text(internal_notes, "Nota interna", optional=True), status=status)
    followup.full_clean()
    followup.save()
    obj.status = status
    obj.version += 1
    obj.save(update_fields=["status", "version", "updated_at"])
    _audit(user, "guardar_seguimiento", followup)
    return followup
