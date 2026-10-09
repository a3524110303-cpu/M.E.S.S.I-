from datetime import date

from django.contrib.auth import get_user_model

from portal.models import (
    CourseGroup,
    Enrollment,
    Indicator,
    Period,
    Profile,
    Student,
    TutorAssignment,
)


class SchoolFixture:
    """Dos periodos y grupos: un alumno compartido detecta fugas por periodo."""

    @classmethod
    def make_user(cls, username, role):
        user = get_user_model().objects.create_user(
            username=username, password="Clave-de-prueba-2026!", first_name=username
        )
        Profile.objects.update_or_create(user=user, defaults={"role": role})
        return user

    @classmethod
    def setUpTestData(cls):
        cls.admin = cls.make_user("admin-test", "admin")
        cls.teacher = cls.make_user("docente-test", "docente")
        cls.other_teacher = cls.make_user("otro-docente", "docente")
        cls.tutor = cls.make_user("tutor-test", "tutor")
        cls.other_tutor = cls.make_user("otro-tutor", "tutor")
        cls.student_user = cls.make_user("alumno-test", "estudiante")
        cls.other_student_user = cls.make_user("otro-alumno", "estudiante")
        cls.student = Student.objects.create(user=cls.student_user, code="EST-001")
        cls.other_student = Student.objects.create(user=cls.other_student_user, code="EST-002")
        cls.period = Period.objects.create(
            name="2026 actual", starts_on=date(2026, 8, 1),
            ends_on=date(2026, 12, 31), is_open=True,
        )
        cls.other_period = Period.objects.create(
            name="2026 anterior", starts_on=date(2026, 1, 1),
            ends_on=date(2026, 6, 30), is_open=True,
        )
        cls.group = CourseGroup.objects.create(
            name="1A", subject="Matemáticas", period=cls.period,
        )
        cls.group.teachers.add(cls.teacher)
        cls.other_group = CourseGroup.objects.create(
            name="1B", subject="Matemáticas", period=cls.period,
        )
        cls.other_group.teachers.add(cls.other_teacher)
        cls.history_group = CourseGroup.objects.create(
            name="1A anterior", subject="Matemáticas", period=cls.other_period,
        )
        cls.history_group.teachers.add(cls.other_teacher)
        cls.enrollment = Enrollment.objects.create(student=cls.student, group=cls.group)
        cls.other_enrollment = Enrollment.objects.create(
            student=cls.other_student, group=cls.other_group,
        )
        cls.history_enrollment = Enrollment.objects.create(
            student=cls.student, group=cls.history_group,
        )
        cls.indicator = Indicator.objects.create(
            enrollment=cls.enrollment, cut="primer_parcial", grade=6, attendance=70,
            homework=80, updated_by=cls.teacher,
        )
        cls.other_indicator = Indicator.objects.create(
            enrollment=cls.other_enrollment, cut="primer_parcial", grade=9,
            attendance=95, homework=98, updated_by=cls.other_teacher,
        )
        cls.history_indicator = Indicator.objects.create(
            enrollment=cls.history_enrollment, cut="primer_parcial", grade=8,
            attendance=90, homework=85, updated_by=cls.other_teacher,
        )
        TutorAssignment.objects.create(
            tutor=cls.tutor, student=cls.student, period=cls.period,
        )
        TutorAssignment.objects.create(
            tutor=cls.other_tutor, student=cls.student, period=cls.other_period,
        )
        TutorAssignment.objects.create(
            tutor=cls.other_tutor, student=cls.other_student, period=cls.period,
        )
