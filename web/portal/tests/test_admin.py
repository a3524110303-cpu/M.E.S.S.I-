from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase

from portal import services
from portal.models import (
    AuditEvent, FollowUp, HelpRequest, Indicator, Prediction, SupportCase,
    TutorAssignment,
)
from portal.tests.fixtures import SchoolFixture


class OrganizationAdminTests(SchoolFixture, TestCase):
    def test_sensitive_academic_and_support_models_are_not_registered_in_admin(self):
        for model in (Indicator, Prediction, HelpRequest, SupportCase, FollowUp):
            with self.subTest(model=model.__name__):
                self.assertNotIn(model, admin.site._registry)

    def test_reassigning_tutor_moves_only_that_period_cases_and_invalidates_old_form(self):
        current_case = services.create_case(
            self.tutor, self.student.pk, self.period.pk, "Acuerdo actual",
        )
        historical_case = services.create_case(
            self.other_tutor, self.student.pk, self.other_period.pk, "Acuerdo anterior",
        )
        original_version = current_case.version
        assignment = TutorAssignment.objects.get(student=self.student, period=self.period)
        assignment.tutor = self.other_tutor
        request = RequestFactory().post("/admin/portal/tutorassignment/")
        request.user = self.admin
        admin.site._registry[TutorAssignment].save_model(request, assignment, None, True)
        current_case.refresh_from_db()
        historical_case.refresh_from_db()
        self.assertEqual(current_case.tutor_id, self.other_tutor.pk)
        self.assertEqual(current_case.version, original_version + 1)
        self.assertEqual(historical_case.version, 1)
        self.assertFalse(services.visible_cases(self.tutor).filter(pk=current_case.pk).exists())
        self.assertTrue(services.visible_cases(self.other_tutor).filter(pk=current_case.pk).exists())
        self.assertTrue(AuditEvent.objects.filter(
            action="reasignar_tutor", entity_id=current_case.pk,
        ).exists())
        with self.assertRaises(PermissionDenied):
            services.add_followup(
                self.tutor, current_case.pk, "Formulario anterior", "", "Cerrado",
                original_version,
            )

    def test_audit_admin_is_read_only(self):
        model_admin = admin.site._registry[AuditEvent]
        request = RequestFactory().get("/admin/portal/auditevent/")
        request.user = self.admin
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))
