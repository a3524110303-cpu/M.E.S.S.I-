from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from portal import services
from portal.models import HelpRequest, Indicator, SupportCase
from portal.tests.fixtures import SchoolFixture


class WebAuthorizationTests(SchoolFixture, TestCase):
    def as_user(self, user, *, csrf=False):
        client = Client(enforce_csrf_checks=csrf)
        client.force_login(user)
        return client

    def edit_payload(self, **updates):
        payload = {
            "cut": "primer_parcial", "grade": "7", "attendance": "80",
            "homework": "85", "expected_version": self.indicator.version,
        }
        payload.update(updates)
        return payload

    def test_anonymous_read_and_write_redirect_to_login(self):
        urls = [
            reverse("portal:teacher"), reverse("portal:student"),
            reverse("portal:tutor"), reverse("portal:export_indicators"),
            reverse("portal:indicator_edit", args=[self.enrollment.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("login"), response.url)
        response = self.client.post(
            reverse("portal:indicator_edit", args=[self.enrollment.pk]), self.edit_payload(),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Indicator.objects.get(pk=self.indicator.pk).grade, 6)

    def test_wrong_role_cannot_open_or_post_teacher_form(self):
        url = reverse("portal:indicator_edit", args=[self.enrollment.pk])
        for user in (self.student_user, self.tutor, self.admin):
            with self.subTest(user=str(user)):
                client = self.as_user(user)
                self.assertEqual(client.get(url).status_code, 403)
                self.assertEqual(client.post(url, self.edit_payload()).status_code, 403)
        self.indicator.refresh_from_db()
        self.assertEqual(self.indicator.grade, 6)

    def test_unprofiled_account_cannot_choose_role_by_parameter(self):
        user = get_user_model().objects.create_user("sin-perfil", password="Clave-de-prueba!")
        client = self.as_user(user)
        response = client.get(reverse("portal:teacher"), {"role": "docente"})
        self.assertEqual(response.status_code, 403)

    def test_staff_flag_does_not_grant_teacher_organization_admin_access(self):
        self.teacher.is_staff = True
        self.teacher.save(update_fields=["is_staff"])
        client = self.as_user(self.teacher)
        response = client.get(reverse("admin:index"))
        self.assertIn(response.status_code, (302, 403))
        self.assertNotContains(response, "portal/tutorassignment", status_code=response.status_code)
        endpoint = reverse("admin:portal_tutorassignment_changelist")
        self.assertIn(client.get(endpoint).status_code, (302, 403))

    def test_teacher_cannot_read_or_modify_foreign_enrollment_by_id(self):
        client = self.as_user(self.teacher)
        url = reverse("portal:indicator_edit", args=[self.other_enrollment.pk])
        self.assertIn(client.get(url).status_code, (403, 404))
        self.assertIn(client.post(url, self.edit_payload()).status_code, (403, 404))
        self.other_indicator.refresh_from_db()
        self.assertEqual(self.other_indicator.grade, 9)

    def test_teacher_export_only_contains_assigned_students(self):
        client = self.as_user(self.teacher)
        response = client.get(reverse("portal:export_indicators"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8-sig")
        self.assertIn(self.student.code, content)
        self.assertNotIn(self.other_student.code, content)
        foreign = client.get(reverse("portal:export_indicators"), {"group": self.other_group.pk})
        self.assertIn(foreign.status_code, (403, 404))

    def test_foreign_import_group_refused_before_any_write(self):
        client = self.as_user(self.teacher)
        url = reverse("portal:import_indicators", args=[self.other_group.pk])
        self.assertIn(client.get(url).status_code, (403, 404))
        self.assertIn(client.post(url, {"cut": "primer_parcial"}).status_code, (403, 404))
        self.assertEqual(Indicator.objects.get(pk=self.other_indicator.pk).grade, 9)

    def test_csrf_blocks_mutating_authenticated_requests(self):
        client = self.as_user(self.teacher, csrf=True)
        url = reverse("portal:indicator_edit", args=[self.enrollment.pk])
        self.assertEqual(client.get(url).status_code, 200)
        self.assertEqual(client.post(url, self.edit_payload()).status_code, 403)
        self.assertEqual(Indicator.objects.get(pk=self.indicator.pk).grade, 6)
        payload = self.edit_payload(csrfmiddlewaretoken=client.cookies["csrftoken"].value)
        self.assertEqual(client.post(url, payload).status_code, 302)
        self.assertEqual(Indicator.objects.get(pk=self.indicator.pk).grade, 7)

    def test_stale_browser_form_reports_conflict_and_preserves_first_change(self):
        client_a = self.as_user(self.teacher)
        client_b = self.as_user(self.teacher)
        url = reverse("portal:indicator_edit", args=[self.enrollment.pk])
        self.assertEqual(client_a.post(url, self.edit_payload(grade="8")).status_code, 302)
        stale = client_b.post(url, self.edit_payload(grade="2"))
        self.assertIn(stale.status_code, (200, 409))
        self.assertContains(stale, "cambi", status_code=stale.status_code)
        self.assertEqual(Indicator.objects.get(pk=self.indicator.pk).grade, 8)

    def test_prediction_and_logout_only_accept_post(self):
        client = self.as_user(self.teacher)
        self.assertEqual(
            client.get(reverse("portal:predict", args=[self.indicator.pk])).status_code, 405,
        )
        self.assertEqual(client.get(reverse("logout")).status_code, 405)

    def test_foreign_case_id_is_hidden_on_get_and_followup_post(self):
        case = services.create_case(
            self.other_tutor, self.other_student.pk, self.period.pk, "Ajeno",
            internal_notes="NOTA_AJENA_8cd84",
        )
        for user in (self.student_user, self.tutor, self.teacher, self.admin):
            with self.subTest(user=str(user)):
                client = self.as_user(user)
                detail = client.get(reverse("portal:case_detail", args=[case.pk]))
                self.assertIn(detail.status_code, (403, 404))
                self.assertNotIn(b"NOTA_AJENA_8cd84", detail.content)
        client = self.as_user(self.tutor)
        response = client.post(reverse("portal:followup_create", args=[case.pk]), {
            "notes": "Ajeno", "internal_notes": "", "status": "Cerrado",
            "expected_version": case.version,
        })
        self.assertIn(response.status_code, (403, 404))
        self.assertEqual(SupportCase.objects.get(pk=case.pk).status, "Pendiente")

    def test_student_detail_hides_internal_notes_and_escapes_public_text(self):
        agreement = '<script>alert("xss")</script> Acuerdo visible'
        case = services.create_case(
            self.tutor, self.student.pk, self.period.pk, agreement,
            internal_notes="PRIVADO_CASO_e031c",
        )
        services.add_followup(
            self.tutor, case.pk, "Avance visible", "PRIVADO_AVANCE_a211f",
            "En seguimiento", case.version,
        )
        client = self.as_user(self.student_user)
        for url in (reverse("portal:student"), reverse("portal:case_detail", args=[case.pk])):
            with self.subTest(url=url):
                response = client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, "PRIVADO_CASO_e031c")
                self.assertNotContains(response, "PRIVADO_AVANCE_a211f")
                self.assertNotContains(response, '<script>alert("xss")</script>')
        detail = client.get(reverse("portal:case_detail", args=[case.pk]))
        self.assertContains(detail, "&lt;script&gt;")
        self.assertContains(detail, "Avance visible")
        tutor_detail = self.as_user(self.tutor).get(reverse("portal:case_detail", args=[case.pk]))
        self.assertContains(tutor_detail, "PRIVADO_CASO_e031c")
        self.assertContains(tutor_detail, "PRIVADO_AVANCE_a211f")

    def test_student_academic_page_renders_only_own_enrollments(self):
        response = self.as_user(self.student_user).get(reverse("portal:student"))
        self.assertContains(response, "Mis indicadores académicos")
        self.assertContains(response, "1A anterior")
        self.assertNotContains(response, "<small>1B</small>")
        self.assertNotContains(response, "otro-alumno")
        own_ids = {item.pk for item in response.context["indicators_page"].object_list}
        self.assertEqual(own_ids, {self.indicator.pk, self.history_indicator.pk})

    def test_invalid_query_identifiers_return_not_found(self):
        teacher_client = self.as_user(self.teacher)
        for endpoint in ("portal:teacher", "portal:export_indicators"):
            with self.subTest(endpoint=endpoint):
                response = teacher_client.get(reverse(endpoint), {"group": "texto-no-id"})
                self.assertEqual(response.status_code, 404)
        response = self.as_user(self.tutor).get(reverse("portal:case_create"), {"request": "texto-no-id"})
        self.assertEqual(response.status_code, 404)

    def test_distinct_authenticated_sessions_share_request_and_followup(self):
        student_client = self.as_user(self.student_user)
        tutor_client = self.as_user(self.tutor)
        teacher_client = self.as_user(self.teacher)
        self.assertNotEqual(student_client.session.session_key, tutor_client.session.session_key)
        self.assertEqual(teacher_client.post(
            reverse("portal:indicator_edit", args=[self.enrollment.pk]),
            self.edit_payload(grade="7.50"),
        ).status_code, 302)
        self.assertEqual(Indicator.objects.get(pk=self.indicator.pk).grade, 7.5)
        response = student_client.post(reverse("portal:request_create"), {
            "period": self.period.pk, "message": "Solicitud desde otra sesión",
        })
        self.assertEqual(response.status_code, 302)
        request = HelpRequest.objects.get(student=self.student)
        self.assertContains(tutor_client.get(reverse("portal:tutor")), request.message)
        response = tutor_client.post(reverse("portal:case_create"), {
            "student": self.student.pk, "period": self.period.pk,
            "request": request.pk, "prediction": "", "agreement": "Acuerdo compartido",
            "internal_notes": "Nota privada",
        })
        self.assertEqual(response.status_code, 302)
        case = SupportCase.objects.get(request=request)
        response = tutor_client.post(reverse("portal:followup_create", args=[case.pk]), {
            "notes": "Avance compartido", "internal_notes": "Nota de tutor",
            "status": "En seguimiento", "expected_version": case.version,
        })
        self.assertEqual(response.status_code, 302)
        detail = student_client.get(reverse("portal:case_detail", args=[case.pk]))
        self.assertContains(detail, "Acuerdo compartido")
        self.assertContains(detail, "Avance compartido")
        self.assertNotContains(detail, "Nota privada")
        self.assertNotContains(detail, "Nota de tutor")

    def test_import_requires_signed_snapshot_of_original_form(self):
        client = self.as_user(self.teacher)
        url = reverse("portal:import_indicators", args=[self.group.pk])
        file = SimpleUploadedFile("indicadores.csv", (
            "id_estudiante,nota_parcial,asistencia,tareas_entregadas\n"
            "EST-001,7,80,85\n"
        ).encode(), content_type="text/csv")
        response = client.post(url, {"cut": "primer_parcial", "file": file, "snapshot": "alterado"})
        self.assertIn(response.status_code, (200, 400))
        self.assertEqual(Indicator.objects.get(pk=self.indicator.pk).grade, 6)

    def import_file(self):
        return SimpleUploadedFile("indicadores.csv", (
            "id_estudiante,nota_parcial,asistencia,tareas_entregadas\n"
            "EST-001,7,80,85\n"
        ).encode(), content_type="text/csv")

    def test_valid_signed_import_form_saves_data(self):
        client = self.as_user(self.teacher)
        url = reverse("portal:import_indicators", args=[self.group.pk])
        form = client.get(url).context["form"]
        response = client.post(url, {
            "cut": "primer_parcial", "file": self.import_file(),
            "snapshot": form["snapshot"].value(),
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Indicator.objects.get(pk=self.indicator.pk).grade, 7)

    def test_signed_import_snapshot_is_bound_to_original_user(self):
        first_client = self.as_user(self.teacher)
        url = reverse("portal:import_indicators", args=[self.group.pk])
        snapshot = first_client.get(url).context["form"]["snapshot"].value()
        self.group.teachers.add(self.other_teacher)
        second_client = self.as_user(self.other_teacher)
        response = second_client.post(url, {
            "cut": "primer_parcial", "file": self.import_file(), "snapshot": snapshot,
        })
        self.assertIn(response.status_code, (200, 400, 403))
        self.assertEqual(Indicator.objects.get(pk=self.indicator.pk).grade, 6)

    def test_signed_import_original_versions_detect_intervening_edits(self):
        client = self.as_user(self.teacher)
        url = reverse("portal:import_indicators", args=[self.group.pk])
        snapshot = client.get(url).context["form"]["snapshot"].value()
        services.save_indicator(
            self.teacher, self.enrollment.pk, "primer_parcial", 8, 95, 95, self.indicator.version,
        )
        response = client.post(url, {
            "cut": "primer_parcial", "file": self.import_file(), "snapshot": snapshot,
        })
        self.assertIn(response.status_code, (200, 409))
        self.assertEqual(Indicator.objects.get(pk=self.indicator.pk).grade, 8)

    def test_export_escapes_excel_formulas_in_organization_names(self):
        import csv
        import io

        self.group.name = "=HYPERLINK(1)"
        self.group.subject = "@SUM(1)"
        self.group.save(update_fields=["name", "subject"])
        response = self.as_user(self.teacher).get(reverse("portal:export_indicators"))
        self.assertEqual(response.status_code, 200)
        row = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))[0]
        self.assertTrue(row["grupo"].startswith("'="))
        self.assertTrue(row["materia"].startswith("'@"))
