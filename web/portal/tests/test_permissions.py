from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from portal import services
from portal.models import FollowUp, HelpRequest, Indicator, SupportCase
from portal.tests.fixtures import SchoolFixture


class ServicePermissionsTests(SchoolFixture, TestCase):
    def test_teacher_sees_only_assigned_group_indicators(self):
        self.assertEqual(
            set(services.visible_indicators(self.teacher).values_list("pk", flat=True)),
            {self.indicator.pk},
        )

    def test_tutor_scope_matches_student_and_period_together(self):
        self.assertEqual(
            set(services.visible_indicators(self.tutor).values_list("pk", flat=True)),
            {self.indicator.pk},
        )
        self.assertEqual(
            set(services.visible_indicators(self.other_tutor).values_list("pk", flat=True)),
            {self.history_indicator.pk, self.other_indicator.pk},
        )

    def test_student_sees_own_indicators_across_periods(self):
        self.assertEqual(
            set(services.visible_indicators(self.student_user).values_list("pk", flat=True)),
            {self.indicator.pk, self.history_indicator.pk},
        )

    def test_unauthenticated_and_admin_accounts_have_no_academic_scope(self):
        for user in (AnonymousUser(), self.admin):
            with self.subTest(user=str(user)):
                self.assertFalse(services.visible_indicators(user).exists())
                self.assertFalse(services.visible_cases(user).exists())
                self.assertFalse(services.visible_requests(user).exists())

    def test_changing_enrollment_id_cannot_write_another_group(self):
        with self.assertRaises(PermissionDenied):
            services.save_indicator(
                self.teacher, self.other_enrollment.pk, "primer_parcial", 1, 1, 1,
                self.other_indicator.version,
            )
        self.other_indicator.refresh_from_db()
        self.assertEqual(self.other_indicator.grade, 9)

    def test_non_teacher_cannot_capture_even_visible_indicator(self):
        for user in (self.student_user, self.tutor, self.admin, AnonymousUser()):
            with self.subTest(user=str(user)), self.assertRaises(PermissionDenied):
                services.save_indicator(
                    user, self.enrollment.pk, "primer_parcial", 1, 1, 1,
                    self.indicator.version,
                )

    def test_request_uses_authenticated_student_identity(self):
        request = services.create_request(self.student_user, self.period.pk, "Necesito ayuda")
        self.assertEqual(request.student_id, self.student.pk)
        self.assertTrue(services.visible_requests(self.tutor).filter(pk=request.pk).exists())
        self.assertFalse(services.visible_requests(self.other_student_user).filter(pk=request.pk).exists())
        self.assertFalse(services.visible_requests(self.other_tutor).filter(pk=request.pk).exists())

    def test_student_cannot_request_an_unenrolled_period(self):
        with self.assertRaises((PermissionDenied, ValidationError)):
            services.create_request(self.other_student_user, self.other_period.pk, "Ayuda")
        self.assertEqual(HelpRequest.objects.count(), 0)

    def test_non_student_cannot_request_support(self):
        for user in (self.teacher, self.tutor, self.admin, AnonymousUser()):
            with self.subTest(user=str(user)), self.assertRaises(PermissionDenied):
                services.create_request(user, self.period.pk, "Ayuda")

    def test_tutor_cannot_create_case_in_another_period_for_same_student(self):
        with self.assertRaises(PermissionDenied):
            services.create_case(
                self.tutor, self.student.pk, self.other_period.pk, "Acuerdo",
            )
        self.assertEqual(SupportCase.objects.count(), 0)

    def test_tutor_cannot_link_request_from_another_student(self):
        foreign_request = services.create_request(
            self.other_student_user, self.period.pk, "Otro alumno",
        )
        with self.assertRaises((PermissionDenied, ValidationError)):
            services.create_case(
                self.tutor, self.student.pk, self.period.pk, "Acuerdo",
                request_id=foreign_request.pk,
            )
        self.assertEqual(SupportCase.objects.count(), 0)

    def test_tutor_cannot_append_followup_to_another_tutor_case(self):
        case = services.create_case(
            self.other_tutor, self.student.pk, self.other_period.pk, "Acuerdo previo",
        )
        with self.assertRaises(PermissionDenied):
            services.add_followup(
                self.tutor, case.pk, "No autorizado", "", "En seguimiento", case.version,
            )
        self.assertEqual(FollowUp.objects.count(), 0)

    def test_request_and_case_queries_do_not_leak_other_period(self):
        current = services.create_request(self.student_user, self.period.pk, "Actual")
        previous = services.create_request(self.student_user, self.other_period.pk, "Anterior")
        current_case = services.create_case(
            self.tutor, self.student.pk, self.period.pk, "Actual", request_id=current.pk,
        )
        previous_case = services.create_case(
            self.other_tutor, self.student.pk, self.other_period.pk,
            "Anterior", request_id=previous.pk,
        )
        self.assertEqual(
            set(services.visible_requests(self.tutor).values_list("pk", flat=True)),
            {current.pk},
        )
        self.assertEqual(
            set(services.visible_cases(self.tutor).values_list("pk", flat=True)),
            {current_case.pk},
        )
        self.assertFalse(services.visible_cases(self.tutor).filter(pk=previous_case.pk).exists())

    def test_indicator_input_validation_rejects_nonfinite_and_out_of_range_values(self):
        for values in ((11, 80, 80), (-1, 80, 80), (6, 101, 80), (6, 80, -1),
                       (float("nan"), 80, 80), (6, float("inf"), 80)):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                services.save_indicator(
                    self.teacher, self.enrollment.pk, "primer_parcial", *values, self.indicator.version,
                )
        self.indicator.refresh_from_db()
        self.assertEqual(self.indicator.grade, 6)

    def test_closed_period_blocks_indicator_changes(self):
        self.period.is_open = False
        self.period.save(update_fields=["is_open"])
        with self.assertRaises(ValidationError):
            services.save_indicator(
                self.teacher, self.enrollment.pk, "primer_parcial", 7, 80, 80, self.indicator.version,
            )
        self.assertEqual(Indicator.objects.get(pk=self.indicator.pk).grade, 6)
