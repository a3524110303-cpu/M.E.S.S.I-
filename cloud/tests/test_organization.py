from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, override_settings

from portal import organization, services
from portal.models import CourseGroup, Enrollment, Period, Profile, Student, TutorAssignment
from portal.tests.fixtures import SchoolFixture


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class CloudOrganizationTests(SchoolFixture, TestCase):
    password = "Nueva-cuenta-cloud-2026!"

    def create_account(self, **updates):
        values = {
            "actor": self.admin, "username": "nuevo-alumno-cloud", "password": self.password,
            "first_name": "Alumno", "last_name": "Nuevo", "role": "estudiante",
            "student_code": "EST-100",
        }
        values.update(updates)
        return organization.create_account(**values)

    def test_all_organization_mutations_require_administrator_role(self):
        for actor in (AnonymousUser(), self.teacher, self.student_user, self.tutor):
            mutations = (
                lambda: organization.create_account(actor, "nuevo", self.password, "A", "B", "docente"),
                lambda: organization.create_period(actor, "Nuevo", date(2027, 1, 1), date(2027, 6, 30)),
                lambda: organization.create_group(actor, "Nuevo", "Materia", self.period.pk, [self.teacher.pk]),
                lambda: organization.enroll_student(actor, self.other_student.pk, self.group.pk),
                lambda: organization.assign_tutor(actor, self.tutor.pk, self.student.pk, self.period.pk),
            )
            for index, mutate in enumerate(mutations):
                with self.subTest(actor=str(actor), mutation=index), self.assertRaises(PermissionDenied):
                    mutate()

    def test_student_account_creates_password_hash_profile_and_student_atomically(self):
        user = self.create_account()
        self.assertTrue(user.check_password(self.password))
        self.assertNotEqual(user.password, self.password)
        self.assertEqual(Profile.objects.get(user=user).role, "estudiante")
        self.assertEqual(Student.objects.get(user=user).code, "EST-100")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_admin_account_gets_staff_and_other_roles_do_not(self):
        for role in ("admin", "docente", "tutor"):
            with self.subTest(role=role):
                user = self.create_account(
                    username="nuevo-" + role, role=role, student_code="",
                )
                self.assertEqual(user.is_staff, role == "admin")
                self.assertFalse(Student.objects.filter(user=user).exists())

    def test_duplicate_username_rejects_without_partial_profile_or_student(self):
        before = (get_user_model().objects.count(), Profile.objects.count(), Student.objects.count())
        with self.assertRaises(ValidationError):
            self.create_account(username=self.teacher.username)
        self.assertEqual(before, (
            get_user_model().objects.count(), Profile.objects.count(), Student.objects.count(),
        ))

    def test_duplicate_student_code_rolls_back_new_user_and_profile(self):
        before = (get_user_model().objects.count(), Profile.objects.count(), Student.objects.count())
        with self.assertRaises(ValidationError):
            self.create_account(student_code=self.student.code)
        self.assertEqual(before, (
            get_user_model().objects.count(), Profile.objects.count(), Student.objects.count(),
        ))

    def test_student_creation_failure_rolls_back_account_and_profile(self):
        before = (get_user_model().objects.count(), Profile.objects.count())
        with patch("portal.organization.Student.save", side_effect=ValidationError("Fallo de prueba")):
            with self.assertRaises(ValidationError):
                self.create_account()
        self.assertEqual(before, (get_user_model().objects.count(), Profile.objects.count()))

    def test_invalid_role_weak_password_and_invalid_student_code_create_nothing(self):
        before = get_user_model().objects.count()
        for changes in ({"role": "director"}, {"password": "123"},
                        {"password": "123456789123"}, {"student_code": "matricula-incorrecta"}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.create_account(**changes)
        self.assertEqual(get_user_model().objects.count(), before)

    def test_non_student_account_cannot_smuggle_student_code(self):
        with self.assertRaises(ValidationError):
            self.create_account(role="docente", student_code="EST-100")
        self.assertFalse(get_user_model().objects.filter(username="nuevo-alumno-cloud").exists())

    def test_valid_period_and_group_are_shared_with_assigned_teacher(self):
        period = organization.create_period(
            self.admin, "2027 primavera", date(2027, 1, 1), date(2027, 6, 30),
        )
        group = organization.create_group(
            self.admin, "2A", "Historia", period.pk, [self.teacher.pk],
        )
        enrollment = organization.enroll_student(self.admin, self.student.pk, group.pk)
        self.assertTrue(services.visible_groups(self.teacher).filter(pk=group.pk).exists())
        self.assertTrue(services.visible_enrollments(self.teacher).filter(pk=enrollment.pk).exists())
        self.assertTrue(services.visible_enrollments(self.student_user).filter(pk=enrollment.pk).exists())

    def test_invalid_period_dates_and_duplicate_period_are_rejected(self):
        before = Period.objects.count()
        with self.assertRaises(ValidationError):
            organization.create_period(self.admin, "Fechas mal", date(2027, 6, 30), date(2027, 1, 1))
        with self.assertRaises(ValidationError):
            organization.create_period(
                self.admin, self.period.name, date(2027, 1, 1), date(2027, 6, 30),
            )
        self.assertEqual(Period.objects.count(), before)

    def test_group_refuses_non_teacher_assignment_and_preserves_atomicity(self):
        before = CourseGroup.objects.count()
        with self.assertRaises(ValidationError):
            organization.create_group(
                self.admin, "Grupo inválido", "Materia", self.period.pk,
                [self.teacher.pk, self.tutor.pk],
            )
        self.assertEqual(CourseGroup.objects.count(), before)

    def test_group_refuses_inactive_teacher(self):
        self.teacher.is_active = False
        self.teacher.save(update_fields=["is_active"])
        with self.assertRaises(ValidationError):
            organization.create_group(self.admin, "Grupo inválido", "Materia", self.period.pk, [self.teacher.pk])
        self.assertFalse(CourseGroup.objects.filter(name="Grupo inválido").exists())

    def test_duplicate_enrollment_does_not_create_duplicate(self):
        before = Enrollment.objects.count()
        with self.assertRaises(ValidationError):
            organization.enroll_student(self.admin, self.student.pk, self.group.pk)
        self.assertEqual(Enrollment.objects.count(), before)

    def test_tutor_assignment_requires_tutor_role_and_student_period_enrollment(self):
        before = TutorAssignment.objects.count()
        for tutor_id, student_id, period_id in (
            (self.teacher.pk, self.student.pk, self.period.pk),
            (self.tutor.pk, self.other_student.pk, self.other_period.pk),
        ):
            with self.subTest(tutor=tutor_id, student=student_id, period=period_id), self.assertRaises(ValidationError):
                organization.assign_tutor(self.admin, tutor_id, student_id, period_id)
        self.assertEqual(TutorAssignment.objects.count(), before)

    def test_reassign_tutor_transfers_cases_and_revokes_previous_access(self):
        case = services.create_case(self.tutor, self.student.pk, self.period.pk, "Acuerdo existente")
        organization.assign_tutor(self.admin, self.other_tutor.pk, self.student.pk, self.period.pk)
        case.refresh_from_db()
        self.assertEqual(case.tutor_id, self.other_tutor.pk)
        self.assertEqual(case.version, 2)
        self.assertFalse(services.visible_cases(self.tutor).filter(pk=case.pk).exists())
        self.assertTrue(services.visible_cases(self.other_tutor).filter(pk=case.pk).exists())
