"""Administración compartida para el portal Streamlit.

Todas las altas validan el rol del actor y se guardan de manera atómica. El
administrador organiza cuentas y grupos; los expedientes siguen sus permisos.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import CourseGroup, Enrollment, Period, Profile, Student, SupportCase, TutorAssignment
from .services import _audit, _require


def _identifier(value):
    if isinstance(value, bool):
        raise ValidationError("Selecciona un registro válido.")
    try:
        result = int(value)
        if result < 1 or str(result) != str(value):
            raise ValueError
        return result
    except (TypeError, ValueError):
        raise ValidationError("Selecciona un registro válido.")


def _record(model, value, *, lock=False):
    query = model.objects.select_for_update() if lock else model.objects
    obj = query.filter(pk=_identifier(value)).first()
    if obj is None:
        raise ValidationError("El registro seleccionado ya no está disponible.")
    return obj


@transaction.atomic
def create_account(actor, username, password, first_name, last_name, role, student_code=""):
    _require(actor, "admin")
    if role not in Profile.Role.values:
        raise ValidationError("Selecciona un rol válido.")
    if not all(isinstance(value, str) for value in (username, password, first_name, last_name, student_code)):
        raise ValidationError("Los datos de la cuenta deben ser texto.")
    if not password:
        raise ValidationError("La contraseña no puede estar vacía.")
    user = get_user_model()(
        username=username.strip(), first_name=first_name.strip(), last_name=last_name.strip(),
        is_active=True, is_staff=role == Profile.Role.ADMIN, is_superuser=False,
    )
    validate_password(password, user)
    user.set_password(password)
    user.full_clean()
    user.save()
    profile = Profile(user=user, role=role)
    profile.full_clean()
    profile.save()
    if role == Profile.Role.STUDENT:
        student = Student(user=user, code=student_code.strip())
        student.full_clean()
        student.save()
    elif student_code.strip():
        raise ValidationError("El código EST- se utiliza sólo para estudiantes.")
    _audit(actor, "crear_cuenta", user)
    return user


@transaction.atomic
def create_period(actor, name, starts_on, ends_on, is_open=True):
    _require(actor, "admin")
    if not isinstance(is_open, bool):
        raise ValidationError("El estado del periodo debe ser abierto o cerrado.")
    period = Period(name=name, starts_on=starts_on, ends_on=ends_on, is_open=is_open)
    period.full_clean()
    period.save()
    _audit(actor, "crear_periodo", period)
    return period


@transaction.atomic
def create_group(actor, name, subject, period_id, teacher_ids):
    _require(actor, "admin")
    period = _record(Period, period_id, lock=True)
    if not isinstance(teacher_ids, (list, tuple, set)):
        raise ValidationError("Selecciona los docentes del grupo.")
    ids = {_identifier(value) for value in teacher_ids}
    teachers = list(get_user_model().objects.filter(
        pk__in=ids, is_active=True, profile__role=Profile.Role.TEACHER,
    ))
    if {teacher.pk for teacher in teachers} != ids:
        raise ValidationError("Todos los docentes deben tener una cuenta activa con ese rol.")
    group = CourseGroup(name=name, subject=subject, period=period)
    group.full_clean()
    group.save()
    group.teachers.set(teachers)
    _audit(actor, "crear_grupo", group)
    return group


@transaction.atomic
def enroll_student(actor, student_id, group_id):
    _require(actor, "admin")
    student = _record(Student, student_id, lock=True)
    group = _record(CourseGroup, group_id, lock=True)
    if not student.user.is_active or not Profile.objects.filter(user_id=student.user_id, role="estudiante").exists():
        raise ValidationError("Selecciona un estudiante con cuenta activa.")
    enrollment = Enrollment(student=student, group=group)
    enrollment.full_clean()
    enrollment.save()
    _audit(actor, "inscribir_estudiante", enrollment)
    return enrollment


@transaction.atomic
def assign_tutor(actor, tutor_id, student_id, period_id):
    _require(actor, "admin")
    # El padre serializa también el alta inicial, cuando aún no hay asignación.
    student = _record(Student, student_id, lock=True)
    period = _record(Period, period_id)
    tutor = _record(get_user_model(), tutor_id)
    assignment = TutorAssignment.objects.select_for_update().filter(student=student, period=period).first()
    if assignment is None:
        assignment = TutorAssignment(student=student, period=period)
    assignment.tutor = tutor
    assignment.full_clean()
    assignment.save()
    # El tutor anterior pierde acceso y el nuevo recibe los casos del periodo.
    for case in SupportCase.objects.select_for_update().filter(student=student, period=period).exclude(tutor=tutor):
        case.tutor = tutor
        case.version += 1
        case.save(update_fields=["tutor", "version", "updated_at"])
        _audit(actor, "reasignar_tutor", case)
    _audit(actor, "asignar_tutor", assignment)
    return assignment
