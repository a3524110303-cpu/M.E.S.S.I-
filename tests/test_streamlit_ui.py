"""QA de Víctor e integración de Marco: Streamlit real con almacenamiento temporal.

Las operaciones MySQL reales se prueban por separado en la suite opt-in.
"""

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app
from messi.storage import SupportStore

STREAMLIT_AVAILABLE = importlib.util.find_spec("streamlit") is not None


@unittest.skipUnless(STREAMLIT_AVAILABLE, "Instala requirements.txt para probar Streamlit.")
class StreamlitInteractionTests(unittest.TestCase):
    def setUp(self):
        from streamlit.testing.v1 import AppTest

        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        synthetic = self.root / "data" / "synthetic"
        synthetic.mkdir(parents=True)
        for name in ("students_demo.csv", "Plantilla_MESSI.xlsx"):
            shutil.copyfile(ROOT / "data" / "synthetic" / name, synthetic / name)
        root_patch = patch.object(app, "ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        import messi.model

        model_patch = patch.object(messi.model, "TRUSTED_MODEL_DIR", self.root / "models")
        model_patch.start()
        self.addCleanup(model_patch.stop)
        self.AppTest = AppTest
        self.store = SupportStore(self.root / "data" / "private" / "messi.sqlite3")
        store_adapter = Mock(wraps=self.store)
        store_adapter.list_indicators = Mock(return_value=[])
        store_adapter.list_predictions = Mock(return_value=[])
        store_patch = patch.object(app, "MySQLStore", return_value=store_adapter)
        store_patch.start()
        self.addCleanup(store_patch.stop)
        config_patch = patch.object(app.MySQLConfig, "from_environment", return_value=object())
        config_patch.start()
        self.addCleanup(config_patch.stop)
        self.ui = self.new_session()

    def new_session(self):
        return self.AppTest.from_string("import app\napp.main()", default_timeout=15).run()

    def choose_source(self, source):
        self.ui.radio[0].set_value(source).run()

    def assert_no_exception(self):
        self.assertEqual(len(self.ui.exception), 0)

    def test_three_roles_render_without_exceptions(self):
        for role, header in (("Docente", "Datos del primer parcial"),
                             ("Estudiante", "Solicitar apoyo"),
                             ("Tutor", "Apoyos y seguimiento")):
            with self.subTest(role=role):
                self.ui.sidebar.radio[0].set_value(role).run()
                self.assert_no_exception()
                self.assertEqual(self.ui.header[0].value, header)

    def test_sample_table_and_missing_model_keep_indicators(self):
        self.choose_source("Ejemplo sintético")
        self.ui.button[0].click().run()
        self.assert_no_exception()
        self.assertEqual(len(self.ui.dataframe[0].value), 8)
        next(button for button in self.ui.button if button.label == "Calcular riesgo de demostración").click().run()
        self.assert_no_exception()
        self.assertIn("Modelo pendiente", self.ui.info[0].value)
        self.assertEqual(len(self.ui.session_state["records"]), 8)
        self.assertNotIn("predictions", self.ui.session_state)

    def test_invalid_paste_discards_old_data_and_reports_reason(self):
        self.choose_source("Pegar tabla")
        self.ui.text_area[0].set_value("EST-901;5,8;70;50")
        self.ui.button[0].click().run()
        self.assertEqual(self.ui.session_state["records"][0]["nota_parcial"], 5.8)
        for invalid in ("EST-901;;70;50", "EST-901;11;70;50",
                        "EST-901;6;101;50", "EST-901;6;70;50\nEST-901;7;80;60"):
            with self.subTest(invalid=invalid):
                self.ui.text_area[0].set_value(invalid)
                self.ui.button[0].click().run()
                self.assert_no_exception()
                self.assertGreater(len(self.ui.error), 0)
                self.assertNotIn("records", self.ui.session_state)

    def test_duplicate_manual_id_preserves_previous_student(self):
        self.choose_source("Captura directa")
        self.ui.text_input[0].set_value("EST-901")
        for field, value in zip(self.ui.number_input, (6.0, 80.0, 70.0)):
            field.set_value(value)
        self.ui.button[0].click().run()
        original = list(self.ui.session_state["records"])
        self.ui.text_input[0].set_value("EST-901")
        for field, value in zip(self.ui.number_input, (7.0, 90.0, 90.0)):
            field.set_value(value)
        self.ui.button[0].click().run()
        self.assert_no_exception()
        self.assertIn("duplicado", self.ui.error[0].value)
        self.assertEqual(self.ui.session_state["records"], original)

    def test_zero_total_is_rejected_and_counts_convert_to_percentages(self):
        self.choose_source("Captura directa")
        self.ui.radio[1].set_value("Cantidades registradas").run()
        self.ui.text_input[0].set_value("EST-902")
        for field, value in zip(self.ui.number_input, (5.8, 0, 0, 2, 4)):
            field.set_value(value)
        self.ui.button[0].click().run()
        self.assert_no_exception()
        self.assertGreater(len(self.ui.error), 0)
        self.assertNotIn("records", self.ui.session_state)
        self.ui.text_input[0].set_value("EST-902")
        for field, value in zip(self.ui.number_input, (5.8, 7, 10, 2, 4)):
            field.set_value(value)
        self.ui.button[0].click().run()
        self.assert_no_exception()
        row = self.ui.session_state["records"][0]
        self.assertEqual((row["asistencia"], row["tareas_entregadas"]), (70.0, 50.0))

    def test_empty_request_does_not_write_to_database(self):
        self.ui.sidebar.radio[0].set_value("Estudiante").run()
        self.ui.text_input[0].set_value("EST-901")
        self.ui.button[0].click().run()
        self.assert_no_exception()
        self.assertIn("vacío", self.ui.error[0].value)
        self.assertEqual(self.store.list_requests(), [])

    def create_request_support_and_followup(self):
        self.ui.sidebar.radio[0].set_value("Estudiante").run()
        self.ui.text_input[0].set_value("EST-901")
        self.ui.text_area[0].set_value("Solicitud ficticia QA sin alerta.")
        self.ui.button[0].click().run()
        self.ui.sidebar.radio[0].set_value("Tutor").run()
        self.ui.text_input[0].set_value("EST-901")
        self.ui.text_area[0].set_value("Acuerdo ficticio de tutoría QA.")
        self.ui.button[0].click().run()
        self.ui.selectbox[2].select("En seguimiento")
        self.ui.text_area[1].set_value("Sesión ficticia QA realizada.")
        self.ui.button[1].click().run()

    def test_request_without_alert_and_followup_survive_new_session(self):
        self.create_request_support_and_followup()
        self.assert_no_exception()
        self.assertNotIn("predictions", self.ui.session_state)
        self.assertEqual(len(self.store.list_requests()), 1)
        self.assertEqual(self.store.list_supports()[0]["status"], "En seguimiento")
        self.assertEqual(len(self.store.list_followups(1)), 1)
        self.ui = self.new_session()
        self.ui.sidebar.radio[0].set_value("Tutor").run()
        self.assert_no_exception()
        self.assertEqual(len(self.ui.dataframe), 3)
        self.assertEqual(self.ui.dataframe[-1].value.iloc[0]["notes"], "Sesión ficticia QA realizada.")

    def test_qa03_followup_keeps_visible_success_confirmation(self):
        """QA-03: la confirmación debe sobrevivir a la actualización de pantalla."""
        self.create_request_support_and_followup()
        self.assertTrue(any(item.value == "Seguimiento guardado." for item in self.ui.success))

    def test_invalid_capture_preserves_inputs_then_success_clears_them(self):
        self.choose_source("Captura directa")
        self.ui.text_input(key="capture_id").set_value("EST-904")
        self.ui.number_input(key="capture_grade").set_value(6.0)
        self.ui.number_input(key="capture_attendance").set_value(80.0)
        self.ui.button[0].click().run()
        self.assertTrue(self.ui.error)
        self.assertEqual(self.ui.text_input(key="capture_id").value, "EST-904")
        self.assertEqual(self.ui.number_input(key="capture_grade").value, 6.0)
        self.ui.number_input(key="capture_homework").set_value(70.0)
        self.ui.button[0].click().run()
        self.assert_no_exception()
        self.assertEqual(len(self.ui.session_state["records"]), 1)
        self.assertEqual(self.ui.text_input(key="capture_id").value, "")
        self.assertIsNone(self.ui.number_input(key="capture_grade").value)

    def test_empty_request_preserves_id_and_success_clears_form(self):
        self.ui.sidebar.radio[0].set_value("Estudiante").run()
        self.ui.text_input(key="request_id").set_value("EST-905")
        self.ui.button[0].click().run()
        self.assertTrue(self.ui.error)
        self.assertEqual(self.ui.text_input(key="request_id").value, "EST-905")
        self.ui.text_area(key="request_message").set_value("Solicitud ficticia.")
        self.ui.button[0].click().run()
        self.assert_no_exception()
        self.assertEqual(len(self.store.list_requests()), 1)
        self.assertEqual(self.ui.text_input(key="request_id").value, "")
        self.assertTrue(any("registrada" in item.value for item in self.ui.success))


if __name__ == "__main__":
    unittest.main()
