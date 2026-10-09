"""Cliente Streamlit: sesiones independientes sobre Django, sin elegir rol."""
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.db import connection
from django.test import SimpleTestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.utils import timezone

from portal import services
from portal.models import FollowUp, HelpRequest, Indicator, Prediction, SupportCase
from portal.tests.fixtures import SchoolFixture


ROOT = Path(__file__).resolve().parents[2]


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
@skipUnlessDBFeature("has_select_for_update")
class CloudStreamlitTests(SchoolFixture, TransactionTestCase):
    def setUp(self):
        from streamlit.testing.v1 import AppTest

        type(self).setUpTestData()
        self.AppTest = AppTest
        flag = patch.dict("os.environ", {"MESSI_CLOUD_LOCAL_TEST": "1"})
        flag.start()
        self.addCleanup(flag.stop)

    def new_app(self):
        app = self.AppTest.from_file(str(ROOT / "cloud" / "app.py"), default_timeout=20)
        database = connection.settings_dict
        app.secrets["messi_web"] = {
            "secret_key": settings.SECRET_KEY, "db_host": database["HOST"],
            "db_name": database["NAME"], "db_user": database["USER"],
            "db_password": database["PASSWORD"], "db_port": database["PORT"],
            "allowed_hosts": ["127.0.0.1"], "csrf_trusted_origins": ["http://127.0.0.1:8501"],
        }
        return app

    def app_for(self, user):
        app = self.new_app()
        app.session_state["_messi_auth_user_id"] = user.pk
        app.session_state["_messi_auth_hash"] = user.get_session_auth_hash()
        app.session_state["_messi_auth_started"] = timezone.now().timestamp()
        app.session_state["_messi_auth_role"] = user.profile.role
        return app.run()

    def output(self, app):
        texts = []
        for category in ("markdown", "caption", "title", "header", "subheader", "info", "warning", "error", "success", "text"):
            texts.extend(str(item.value) for item in getattr(app, category))
        texts.extend(str(item.value) for item in app.dataframe)
        return "\n".join(texts)

    def test_each_session_renders_only_its_authenticated_role(self):
        roles = (
            (self.teacher, "ESPACIO DOCENTE"),
            (self.student_user, "ESPACIO ESTUDIANTE"),
            (self.tutor, "ESPACIO TUTOR"),
            (self.admin, "ORGANIZACIÓN ESCOLAR"),
        )
        for user, expected in roles:
            with self.subTest(role=user.profile.role):
                app = self.app_for(user)
                self.assertEqual(len(app.exception), 0)
                output = self.output(app)
                self.assertIn(expected, output)
                for _, other_heading in roles:
                    if other_heading != expected:
                        self.assertNotIn(other_heading, output)

    def test_student_session_contains_only_own_indicators_and_public_case_data(self):
        request = services.create_request(self.student_user, self.period.pk, "Solicitud pública QA")
        case = services.create_case(
            self.tutor, self.student.pk, self.period.pk, "Acuerdo público QA",
            internal_notes="PRIVADO_CASO_CLOUD_3942", request_id=request.pk,
        )
        services.add_followup(
            self.tutor, case.pk, "Avance público QA", "PRIVADO_AVANCE_CLOUD_9842",
            "En seguimiento", case.version,
        )
        app = self.app_for(self.student_user)
        self.assertEqual(len(app.exception), 0)
        output = self.output(app)
        self.assertIn("Acuerdo público QA", output)
        self.assertIn("Avance público QA", output)
        self.assertNotIn("PRIVADO_CASO_CLOUD_3942", output)
        self.assertNotIn("PRIVADO_AVANCE_CLOUD_9842", output)
        self.assertNotIn(self.other_student.code, output)

    def test_independent_tutor_sessions_do_not_share_private_case_cache(self):
        services.create_case(
            self.tutor, self.student.pk, self.period.pk, "Acuerdo tutor A",
            internal_notes="PRIVADO_TUTOR_A_a84e",
        )
        services.create_case(
            self.other_tutor, self.other_student.pk, self.period.pk, "Acuerdo tutor B",
            internal_notes="PRIVADO_TUTOR_B_738d",
        )
        first = self.app_for(self.tutor)
        second = self.app_for(self.other_tutor)
        self.assertEqual(len(first.exception), 0)
        self.assertEqual(len(second.exception), 0)
        first_output = self.output(first)
        second_output = self.output(second)
        self.assertIn("Acuerdo tutor A", first_output)
        self.assertNotIn("Acuerdo tutor B", first_output)
        self.assertIn("Acuerdo tutor B", second_output)
        self.assertNotIn("Acuerdo tutor A", second_output)
        self.assertNotIn("PRIVADO_TUTOR_B_738d", first_output)
        self.assertNotIn("PRIVADO_TUTOR_A_a84e", second_output)

    def test_restricted_role_has_no_free_role_selector(self):
        for user in (self.teacher, self.student_user, self.tutor):
            with self.subTest(role=user.profile.role):
                app = self.app_for(user)
                self.assertEqual(len(app.exception), 0)
                labels = [item.label.casefold() for item in (*app.selectbox, *app.radio)]
                self.assertFalse(any(label in ("rol", "selecciona tu rol", "perfil") for label in labels))

    def test_login_form_authenticates_and_clears_plaintext_password(self):
        app = self.new_app().run()
        self.assertEqual(len(app.exception), 0)
        app.text_input(key="_messi_login_username").set_value(self.teacher.username)
        app.text_input(key="_messi_login_password").set_value("Clave-de-prueba-2026!")
        next(button for button in app.button if button.label == "Entrar").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn("ESPACIO DOCENTE", self.output(app))
        self.assertEqual(app.session_state["_messi_auth_user_id"], self.teacher.pk)
        self.assertFalse(any(
            isinstance(value, str) and value == "Clave-de-prueba-2026!"
            for value in app.session_state.values()
        ))

    def click(self, app, label):
        buttons = [button for button in app.button if button.label == label]
        self.assertEqual(len(buttons), 1)
        buttons[0].click().run()
        self.assertEqual(len(app.exception), 0)

    def test_three_cloud_sessions_submit_complete_shared_support_workflow(self):
        teacher = self.app_for(self.teacher)
        prefix = f"messi-ui-{self.teacher.pk}-indicator-{self.enrollment.pk}"
        teacher.number_input(key=prefix + "-grade").set_value(7.5)
        teacher.number_input(key=prefix + "-attendance").set_value(80.0)
        teacher.number_input(key=prefix + "-homework").set_value(85.0)
        self.click(teacher, "Guardar indicadores")
        self.assertEqual(Indicator.objects.get(pk=self.indicator.pk).grade, 7.5)
        self.click(teacher, "Calcular riesgo demostrativo")
        self.assertEqual(Prediction.objects.filter(indicator=self.indicator).count(), 1)

        student = self.app_for(self.student_user)
        next(field for field in student.text_area if field.label == "¿En qué necesitas apoyo?").set_value("Ayuda enviada desde cliente Cloud")
        self.click(student, "Enviar solicitud")
        request = HelpRequest.objects.get(student=self.student)
        self.assertEqual(request.message, "Ayuda enviada desde cliente Cloud")

        tutor = self.app_for(self.tutor)
        self.assertIn(request.message, self.output(tutor))
        next(field for field in tutor.text_area if field.label == "Acuerdo de apoyo visible al estudiante").set_value("Acuerdo de cliente Cloud")
        next(field for field in tutor.text_area if field.label == "Notas privadas del tutor").set_value("PRIVADO_CLOUD_WORKFLOW_e19c")
        self.click(tutor, "Crear caso de apoyo")
        case = SupportCase.objects.get(request=request)
        prefix = f"messi-ui-{self.tutor.pk}-followup-{case.pk}"
        tutor.text_area(key=prefix + "-notes").set_value("Avance de cliente Cloud")
        tutor.text_area(key=prefix + "-internal").set_value("PRIVADO_CLOUD_AVANCE_604e")
        tutor.selectbox(key=prefix + "-status").set_value("En seguimiento")
        self.click(tutor, "Guardar seguimiento")
        self.assertEqual(FollowUp.objects.filter(case=case).count(), 1)
        self.assertEqual(SupportCase.objects.get(pk=case.pk).status, "En seguimiento")

        student.run()
        self.assertEqual(len(student.exception), 0)
        public = self.output(student)
        self.assertIn("Acuerdo de cliente Cloud", public)
        self.assertIn("Avance de cliente Cloud", public)
        self.assertNotIn("PRIVADO_CLOUD_WORKFLOW_e19c", public)
        self.assertNotIn("PRIVADO_CLOUD_AVANCE_604e", public)


class MissingCloudConfigurationSmokeTests(SimpleTestCase):
    def test_apptest_without_settings_shows_safe_message_and_stops(self):
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_file(str(ROOT / "cloud" / "app.py"), default_timeout=20)
        # Un diccionario no vacío evita que AppTest cargue Secrets reales.
        app.secrets["unrelated_test_setting"] = True
        app.run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 1)
        self.assertIn("[messi_web]", app.error[0].value)
        self.assertFalse(any(field.label == "Contraseña" for field in app.text_input))
