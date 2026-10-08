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
from messi.sqlite_storage import SQLiteStore

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
        self.store = SQLiteStore(self.root / "data" / "private" / "messi.sqlite3")
        store_patch = patch.object(app, "SQLiteStore", return_value=self.store)
        store_patch.start()
        self.addCleanup(store_patch.stop)
        self.ui = self.new_session()

    def new_session(self):
        return self.AppTest.from_string("import app\napp.main()", default_timeout=15).run()

    def choose_source(self, source):
        self.ui.radio[0].set_value(source).run()

    def assert_no_exception(self):
        self.assertEqual(len(self.ui.exception), 0)

    def click(self, label):
        """Accionar por intención, independiente del orden de las columnas."""
        buttons = [button for button in self.ui.button if button.label == label]
        self.assertEqual(len(buttons), 1, f"Se esperaba una acción única: {label}")
        buttons[0].click().run()

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
        self.click("Cargar ejemplo sintético")
        self.assert_no_exception()
        self.assertEqual(len(self.ui.dataframe[0].value), 8)
        self.click("Calcular riesgo de demostración")
        self.assert_no_exception()
        self.assertTrue(any("Modelo pendiente" in item.value for item in self.ui.info))
        self.assertEqual(len(self.ui.session_state["records"]), 8)
        self.assertNotIn("predictions", self.ui.session_state)

    def test_invalid_paste_discards_old_data_and_reports_reason(self):
        self.choose_source("Pegar tabla")
        self.ui.text_area[0].set_value("EST-901;5,8;70;50")
        self.click("Revisar tabla pegada")
        self.assertEqual(self.ui.session_state["records"][0]["nota_parcial"], 5.8)
        for invalid in ("EST-901;;70;50", "EST-901;11;70;50",
                        "EST-901;6;101;50", "EST-901;6;70;50\nEST-901;7;80;60"):
            with self.subTest(invalid=invalid):
                self.ui.text_area[0].set_value(invalid)
                self.click("Revisar tabla pegada")
                self.assert_no_exception()
                self.assertGreater(len(self.ui.error), 0)
                self.assertNotIn("records", self.ui.session_state)

    def test_duplicate_manual_id_preserves_previous_student(self):
        self.choose_source("Captura directa")
        self.ui.text_input(key="capture_id").set_value("EST-901")
        for key, value in (("capture_grade", 6.0), ("capture_attendance", 80.0), ("capture_homework", 70.0)):
            self.ui.number_input(key=key).set_value(value)
        self.click("Agregar estudiante")
        original = list(self.ui.session_state["records"])
        self.ui.text_input(key="capture_id").set_value("EST-901")
        for key, value in (("capture_grade", 7.0), ("capture_attendance", 90.0), ("capture_homework", 90.0)):
            self.ui.number_input(key=key).set_value(value)
        self.click("Agregar estudiante")
        self.assert_no_exception()
        self.assertIn("duplicado", self.ui.error[0].value)
        self.assertEqual(self.ui.session_state["records"], original)

    def test_zero_total_is_rejected_and_counts_convert_to_percentages(self):
        self.choose_source("Captura directa")
        self.ui.radio[1].set_value("Cantidades registradas").run()
        self.ui.text_input(key="capture_id").set_value("EST-902")
        for key, value in (("capture_grade", 5.8), ("capture_attendance_count", 0), ("capture_sessions_count", 0), ("capture_homework_count", 2), ("capture_assigned_count", 4)):
            self.ui.number_input(key=key).set_value(value)
        self.click("Agregar estudiante")
        self.assert_no_exception()
        self.assertGreater(len(self.ui.error), 0)
        self.assertNotIn("records", self.ui.session_state)
        self.ui.text_input(key="capture_id").set_value("EST-902")
        for key, value in (("capture_grade", 5.8), ("capture_attendance_count", 7), ("capture_sessions_count", 10), ("capture_homework_count", 2), ("capture_assigned_count", 4)):
            self.ui.number_input(key=key).set_value(value)
        self.click("Agregar estudiante")
        self.assert_no_exception()
        row = self.ui.session_state["records"][0]
        self.assertEqual((row["asistencia"], row["tareas_entregadas"]), (70.0, 50.0))

    def test_empty_request_does_not_write_to_database(self):
        self.ui.sidebar.radio[0].set_value("Estudiante").run()
        self.ui.text_input(key="request_id").set_value("EST-901")
        self.click("Enviar solicitud")
        self.assert_no_exception()
        self.assertIn("vacío", self.ui.error[0].value)
        self.assertEqual(self.store.list_requests(), [])

    def create_request_support_and_followup(self):
        self.ui.sidebar.radio[0].set_value("Estudiante").run()
        self.ui.text_input(key="request_id").set_value("EST-901")
        self.ui.text_area(key="request_message").set_value("Solicitud ficticia QA sin alerta.")
        self.click("Enviar solicitud")
        self.ui.sidebar.radio[0].set_value("Tutor").run()
        self.ui.text_input(key="support_student_id").set_value("EST-901")
        self.ui.text_area(key="support_notes").set_value("Acuerdo ficticio de tutoría QA.")
        self.click("Registrar apoyo")
        next(field for field in self.ui.selectbox if field.label == "Estado del apoyo").select("En seguimiento")
        self.ui.text_area(key="followup_notes").set_value("Sesión ficticia QA realizada.")
        self.click("Guardar seguimiento")

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
        history = next(frame.value for frame in self.ui.dataframe if "Folio del apoyo" in frame.value.columns)
        self.assertEqual(history.iloc[0]["Nota"], "Sesión ficticia QA realizada.")

    def test_tutor_tables_translate_labels_and_preserve_stored_records(self):
        request = self.store.create_request("EST-906", "Solicitud ficticia sin alerta")
        support = self.store.create_support("EST-906", "Tutoria", "Acuerdo ficticio")
        self.store.add_followup(support, "Seguimiento ficticio", "En seguimiento")
        stored = (self.store.list_requests(), self.store.list_supports(), self.store.list_followups(support))
        self.ui.sidebar.radio[0].set_value("Tutor").run()
        self.assert_no_exception()
        tables = [frame.value for frame in self.ui.dataframe]
        inbox = next(table for table in tables if "Solicitud" in table.columns)
        agreements = next(table for table in tables if "Tipo de apoyo" in table.columns)
        history = next(table for table in tables if "Folio del apoyo" in table.columns)
        self.assertEqual(inbox.iloc[0]["Folio"], request)
        self.assertEqual(inbox.iloc[0]["Código del estudiante"], "EST-906")
        self.assertEqual(inbox.iloc[0]["Solicitud"], "Solicitud ficticia sin alerta")
        self.assertEqual(agreements.iloc[0]["Folio"], support)
        self.assertEqual(agreements.iloc[0]["Tipo de apoyo"], "Tutoría académica")
        self.assertEqual(agreements.iloc[0]["Estado"], "En seguimiento")
        self.assertEqual(history.iloc[0]["Folio del apoyo"], support)
        self.assertEqual(history.iloc[0]["Nota"], "Seguimiento ficticio")
        self.assertIn("Fecha (hora local)", inbox.columns)
        self.assertEqual((self.store.list_requests(), self.store.list_supports(), self.store.list_followups(support)), stored)

    def test_qa03_followup_keeps_visible_success_confirmation(self):
        """QA-03: la confirmación debe sobrevivir a la actualización de pantalla."""
        self.create_request_support_and_followup()
        self.assertTrue(any(item.value == "Seguimiento guardado." for item in self.ui.success))

    def test_invalid_capture_preserves_inputs_then_success_clears_them(self):
        self.choose_source("Captura directa")
        self.ui.text_input(key="capture_id").set_value("EST-904")
        self.ui.number_input(key="capture_grade").set_value(6.0)
        self.ui.number_input(key="capture_attendance").set_value(80.0)
        self.click("Agregar estudiante")
        self.assertTrue(self.ui.error)
        self.assertEqual(self.ui.text_input(key="capture_id").value, "EST-904")
        self.assertEqual(self.ui.number_input(key="capture_grade").value, 6.0)
        self.ui.number_input(key="capture_homework").set_value(70.0)
        self.click("Agregar estudiante")
        self.assert_no_exception()
        self.assertEqual(len(self.ui.session_state["records"]), 1)
        self.assertEqual(self.ui.text_input(key="capture_id").value, "")
        self.assertIsNone(self.ui.number_input(key="capture_grade").value)

    def test_empty_request_preserves_id_and_success_clears_form(self):
        self.ui.sidebar.radio[0].set_value("Estudiante").run()
        self.ui.text_input(key="request_id").set_value("EST-905")
        self.click("Enviar solicitud")
        self.assertTrue(self.ui.error)
        self.assertEqual(self.ui.text_input(key="request_id").value, "EST-905")
        self.ui.text_area(key="request_message").set_value("Solicitud ficticia.")
        self.click("Enviar solicitud")
        self.assert_no_exception()
        self.assertEqual(len(self.store.list_requests()), 1)
        self.assertEqual(self.ui.text_input(key="request_id").value, "")
        self.assertTrue(any("registrada" in item.value for item in self.ui.success))


if __name__ == "__main__":
    unittest.main()
