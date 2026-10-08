"""Regresiones de estado y rutas de la interfaz, sin abrir Streamlit.

La comprobación visual y las interacciones reales requieren Streamlit instalado.
"""

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app


class FakeUI:
    def __init__(self, source="Ejemplo sintético", role="Docente"):
        self.session_state = {}
        self.sidebar = self
        self.source, self.role = source, role
        self.buttons = set()
        self.messages = []
        self.numeric = {}
        self.text = {}
        self.selections = {}
        self.counts = False
        self.reruns = 0
        self.uploaded = None
        self.metrics = []
        self.dataframes = []
        self.markdowns = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def radio(self, label, options, **kwargs):
        if list(options) == ["Docente", "Tutor", "Estudiante"]:
            return self.role
        if list(options) == ["Porcentajes", "Cantidades registradas"]:
            return options[1 if self.counts else 0]
        return self.source

    def button(self, label, **kwargs):
        return label in self.buttons

    form_submit_button = button

    def form(self, *args, **kwargs):
        return self

    def columns(self, spec, **kwargs):
        return [self] * (spec if isinstance(spec, int) else len(spec))

    def container(self, *args, **kwargs):
        return self

    def expander(self, *args, **kwargs):
        return self

    def empty(self):
        return self

    def markdown(self, body, **kwargs):
        self.markdowns.append(body)

    def metric(self, label, value, delta=None, **kwargs):
        self.metrics.append({"label": label, "value": value, "delta": delta})

    def dataframe(self, data, **kwargs):
        self.dataframes.append(data)

    def number_input(self, label, **kwargs):
        return self.numeric.get(kwargs.get("key"), self.numeric.get(label))

    def text_input(self, label, **kwargs):
        return self.text.get(kwargs.get("key"), self.text.get(label, ""))

    def text_area(self, label, **kwargs):
        return self.text.get(kwargs.get("key"), self.text.get(label, ""))

    def file_uploader(self, *args, **kwargs):
        return self.uploaded

    def selectbox(self, label, options, **kwargs):
        return self.selections.get(kwargs.get("key"), self.selections.get(label, options[kwargs.get("index", 0)]))

    def rerun(self):
        self.reruns += 1

    def error(self, message):
        self.messages.append(("error", message))

    def info(self, message):
        self.messages.append(("info", message))

    def warning(self, message):
        self.messages.append(("warning", message))

    def success(self, message):
        self.messages.append(("success", message))

    def __getattr__(self, name):
        if name in {"set_page_config", "title", "write", "caption", "header", "subheader", "download_button", "divider"}:
            return lambda *args, **kwargs: None
        raise AttributeError(name)


class AppRegressionTests(unittest.TestCase):
    def test_example_remains_selected_on_prediction_rerun(self):
        ui = FakeUI()
        ui.buttons.add("Cargar ejemplo sintético")
        app.show_teacher(ui)
        records = ui.session_state["records"]
        self.assertEqual(len(records), 8)
        ui.buttons = {"Calcular riesgo de demostración"}
        with patch.object(app, "score_records", side_effect=app.ModelUnavailable("Modelo pendiente")):
            app.show_teacher(ui)
        self.assertEqual(ui.session_state["records"], records)
        self.assertNotIn("predictions", ui.session_state)
        self.assertIn(("info", "Modelo pendiente"), ui.messages)

    def test_changing_source_clears_old_data_and_predictions(self):
        ui = FakeUI(source="Excel o CSV")
        ui.session_state.update(input_source="Ejemplo sintético", records=[{"old": 1}], predictions=[{"old": 1}], saved_fingerprint="old", predictions_saved=True)
        app.show_teacher(ui)
        self.assertNotIn("records", ui.session_state)
        self.assertNotIn("predictions", ui.session_state)
        self.assertNotIn("saved_fingerprint", ui.session_state)
        self.assertNotIn("predictions_saved", ui.session_state)

    def test_bad_paste_clears_previous_predictions(self):
        ui = FakeUI(source="Pegar tabla")
        ui.session_state.update(input_source="Pegar tabla", records=[{"old": 1}], predictions=[{"old": 1}])
        ui.buttons.add("Revisar tabla pegada")
        ui.text["Tabla del primer parcial"] = "datos incompletos"
        app.show_teacher(ui)
        self.assertTrue(any(kind == "error" for kind, _ in ui.messages))
        self.assertNotIn("records", ui.session_state)
        self.assertNotIn("predictions", ui.session_state)

    def test_manual_counts_create_same_percentage_contract(self):
        ui = FakeUI(source="Captura directa")
        ui.counts = True
        ui.buttons.add("Agregar estudiante")
        ui.numeric = {"Nota del primer parcial": 5.8, "Sesiones asistidas": 7, "Sesiones impartidas": 10, "Tareas entregadas": 2, "Tareas solicitadas": 4}
        app.show_teacher(ui)
        self.assertEqual(ui.session_state["records"], [{"id_estudiante": "EST-0001", "nota_parcial": 5.8, "asistencia": 70.0, "tareas_entregadas": 50.0}])

    def test_storage_failure_does_not_block_teacher(self):
        ui = FakeUI(role="Docente")
        with patch.dict(sys.modules, {"streamlit": ui}), \
                patch.object(app, "SQLiteStore", side_effect=app.DatabaseError("SQLite no configurado")) as store:
            app.main()
        store.assert_called_once()
        self.assertFalse(any(kind == "error" for kind, _ in ui.messages))

    def test_invalid_manual_addition_preserves_captured_rows(self):
        ui = FakeUI(source="Captura directa")
        existing = [{"id_estudiante": "EST-0001", "nota_parcial": 6.0, "asistencia": 80.0, "tareas_entregadas": 70.0}]
        ui.session_state.update(input_source="Captura directa", records=existing)
        ui.buttons.add("Agregar estudiante")
        app.show_teacher(ui)  # Campos nuevos vacíos, sin perder la fila previa.
        self.assertEqual(ui.session_state["records"], existing)
        self.assertTrue(any(kind == "error" for kind, _ in ui.messages))

    def test_missing_sqlite_is_reported_to_tutor(self):
        ui = FakeUI(role="Tutor")
        with patch.dict(sys.modules, {"streamlit": ui}), \
                patch.object(app, "SQLiteStore", side_effect=app.DatabaseError("SQLite no disponible")):
            app.main()
        self.assertTrue(any(kind == "error" and "registro de apoyos" in message for kind, message in ui.messages))


class AppSQLiteTests(unittest.TestCase):
    RECORDS = [{"id_estudiante": "EST-001", "nota_parcial": 6.0, "asistencia": 80.0, "tareas_entregadas": 70.0}]
    PREDICTIONS = [{**RECORDS[0], "puntuacion_riesgo": 0.35, "alerta": False, "origen_modelo": "demo_sintetica"}]

    def store(self):
        store = Mock(spec=app.SQLiteStore)
        for name in ("list_indicators", "list_predictions", "list_requests", "list_supports", "list_followups"):
            getattr(store, name).return_value = []
        store.create_request.return_value = 7
        store.create_support.return_value = 9
        return store

    def teacher(self):
        ui = FakeUI()
        ui.session_state.update(input_source=ui.source, records=self.RECORDS.copy())
        return ui

    def test_main_uses_sqlite_configuration_without_eager_operations(self):
        ui = FakeUI(role="Docente")
        store = self.store()
        path = Path("temporary-messi.sqlite3")
        with patch.dict(sys.modules, {"streamlit": ui}), \
                patch.object(app, "database_path", return_value=path) as read_path, \
                patch.object(app, "SQLiteStore", return_value=store) as create_store:
            app.main()
        read_path.assert_called_once_with()
        create_store.assert_called_once_with(path)
        self.assertEqual(store.mock_calls, [])
        self.assertFalse(any(kind == "error" for kind, _ in ui.messages))

    def test_indicators_are_saved_only_when_requested(self):
        ui = self.teacher()
        store = self.store()
        app.show_teacher(ui, store)
        store.save_indicators.assert_not_called()
        ui.buttons = {"Guardar indicadores"}
        app.show_teacher(ui, store)
        store.save_indicators.assert_called_once_with(self.RECORDS, period="primer_parcial")
        ui.buttons.clear()
        app.show_teacher(ui, store)
        store.save_indicators.assert_called_once()

    def test_loading_sqlite_records_survives_excel_rerun_without_upload(self):
        ui = FakeUI(source="Excel o CSV")
        ui.buttons = {"Cargar indicadores guardados"}
        store = self.store()
        store.list_indicators.return_value = self.RECORDS.copy()
        app.show_teacher(ui, store)
        self.assertEqual(ui.session_state["records"], self.RECORDS)
        self.assertEqual(ui.session_state["records_origin"], "database")
        store.list_indicators.assert_called_once_with(period="primer_parcial")
        ui.buttons.clear()
        app.show_teacher(ui, store)
        self.assertEqual(ui.session_state["records"], self.RECORDS)
        store.list_indicators.assert_called_once()
        store.save_indicators.assert_not_called()

    def test_loading_indicators_discards_predictions_for_other_records(self):
        ui = self.teacher()
        ui.session_state["predictions"] = self.PREDICTIONS.copy()
        ui.buttons = {"Cargar indicadores guardados"}
        store = self.store()
        store.list_indicators.return_value = self.RECORDS.copy()
        app.show_teacher(ui, store)
        self.assertNotIn("predictions", ui.session_state)

    def test_loaded_sqlite_records_survive_existing_upload_until_file_changes(self):
        ui = FakeUI(source="Excel o CSV")
        csv_data = b"id_estudiante,nota_parcial,asistencia,tareas_entregadas\nEST-002,5,60,40\n"
        ui.uploaded = SimpleNamespace(name="captura.csv", getvalue=lambda: csv_data)
        ui.buttons = {"Cargar indicadores guardados"}
        store = self.store()
        store.list_indicators.return_value = self.RECORDS.copy()
        app.show_teacher(ui, store)
        ui.buttons.clear()
        app.show_teacher(ui, store)
        self.assertEqual(ui.session_state["records"], self.RECORDS)
        new_csv = b"id_estudiante,nota_parcial,asistencia,tareas_entregadas\nEST-003,7,90,85\n"
        ui.uploaded = SimpleNamespace(name="nueva.csv", getvalue=lambda: new_csv)
        app.show_teacher(ui, store)
        self.assertEqual(ui.session_state["records"][0]["id_estudiante"], "EST-003")
        store.list_indicators.assert_called_once()
        store.save_indicators.assert_not_called()

    def test_save_failure_keeps_captured_records_and_reports_sqlite(self):
        ui = self.teacher()
        ui.buttons = {"Guardar indicadores"}
        store = self.store()
        store.save_indicators.side_effect = app.DatabaseError("Servidor SQLite no disponible")
        app.show_teacher(ui, store)
        self.assertEqual(ui.session_state["records"], self.RECORDS)
        self.assertNotIn("saved_fingerprint", ui.session_state)
        self.assertTrue(any(kind == "error" and "guardar" in message and "SQLite" in message for kind, message in ui.messages))

    def test_load_failure_keeps_current_records_and_reports_sqlite(self):
        ui = self.teacher()
        ui.buttons = {"Cargar indicadores guardados"}
        store = self.store()
        store.list_indicators.side_effect = app.DatabaseError("Servidor SQLite no disponible")
        app.show_teacher(ui, store)
        self.assertEqual(ui.session_state["records"], self.RECORDS)
        self.assertTrue(any(kind == "error" and "cargar" in message and "SQLite" in message for kind, message in ui.messages))

    def test_no_sqlite_config_error_until_explicit_persistence(self):
        ui = self.teacher()
        app.show_teacher(ui, storage_error=app.DatabaseError("Configura SQLite"))
        self.assertFalse(any(kind == "error" for kind, _ in ui.messages))
        ui.buttons = {"Guardar indicadores"}
        app.show_teacher(ui, storage_error=app.DatabaseError("Configura SQLite"))
        self.assertTrue(any(kind == "error" and "Configura SQLite" in message for kind, message in ui.messages))

    def test_prediction_is_saved_on_calculation_only(self):
        ui = self.teacher()
        ui.buttons = {"Calcular riesgo de demostración"}
        store = self.store()
        with patch.object(app, "score_records", return_value=self.PREDICTIONS.copy()):
            app.show_teacher(ui, store)
        self.assertEqual(ui.session_state["predictions"], self.PREDICTIONS)
        self.assertTrue(ui.session_state["predictions_saved"])
        self.assertEqual(ui.session_state["saved_fingerprint"], app.records_fingerprint(self.RECORDS))
        store.save_predictions.assert_called_once_with(self.PREDICTIONS, period="primer_parcial")
        ui.buttons.clear()
        app.show_teacher(ui, store)
        store.save_predictions.assert_called_once()

    def test_prediction_survives_sqlite_failure(self):
        ui = self.teacher()
        ui.buttons = {"Calcular riesgo de demostración"}
        store = self.store()
        store.save_predictions.side_effect = app.DatabaseError("SQLite sin conexión")
        with patch.object(app, "score_records", return_value=self.PREDICTIONS.copy()):
            app.show_teacher(ui, store)
        self.assertEqual(ui.session_state["predictions"], self.PREDICTIONS)
        self.assertFalse(ui.session_state.get("predictions_saved", False))
        self.assertNotIn("saved_fingerprint", ui.session_state)
        self.assertTrue(any(kind == "warning" and "sesión" in message and "SQLite" in message for kind, message in ui.messages))

    def test_bad_paste_resets_saved_status_and_visible_progress(self):
        ui = FakeUI(source="Pegar tabla")
        ui.session_state.update(input_source=ui.source, records=self.RECORDS.copy(), predictions=self.PREDICTIONS.copy(), saved_fingerprint=app.records_fingerprint(self.RECORDS), predictions_saved=True)
        ui.buttons.add("Revisar tabla pegada")
        ui.text["Tabla del primer parcial"] = "EST-001;12;80;70"
        with patch.object(app, "teacher_steps") as render_progress:
            app.show_teacher(ui, self.store())
        self.assertTrue(any(kind == "error" for kind, _ in ui.messages))
        for key in ("records", "predictions", "saved_fingerprint", "predictions_saved"):
            self.assertNotIn(key, ui.session_state)
        render_progress.assert_called_with(ui, loaded=False, saved=False, calculated=False)

    def test_replacing_saved_data_invalidates_result_and_guarded_progress(self):
        ui = self.teacher()
        ui.session_state.update(predictions=self.PREDICTIONS.copy(), saved_fingerprint=app.records_fingerprint(self.RECORDS), predictions_saved=True)
        changed = [{**self.RECORDS[0], "nota_parcial": 7.0}]
        app.accept_records(ui, changed)
        with patch.object(app, "teacher_steps") as render_progress:
            app.show_teacher(ui, self.store())
        self.assertEqual(ui.session_state["records"], changed)
        for key in ("predictions", "saved_fingerprint", "predictions_saved"):
            self.assertNotIn(key, ui.session_state)
        render_progress.assert_called_with(ui, loaded=True, saved=False, calculated=False)

    def test_model_unavailable_does_not_attempt_sqlite_save(self):
        ui = self.teacher()
        ui.buttons = {"Calcular riesgo de demostración"}
        store = self.store()
        with patch.object(app, "score_records", side_effect=app.ModelUnavailable("Modelo pendiente")):
            app.show_teacher(ui, store)
        store.save_predictions.assert_not_called()
        self.assertNotIn("predictions", ui.session_state)

    def test_tutor_restores_indicators_and_predictions_from_sqlite(self):
        ui = FakeUI(role="Tutor")
        store = self.store()
        store.list_indicators.return_value = self.RECORDS.copy()
        stored_predictions = [{**self.PREDICTIONS[0], "period": "primer_parcial", "created_at": "2026-10-03T12:00:00"}]
        store.list_predictions.return_value = stored_predictions
        app.show_tutor(ui, store)
        self.assertEqual(ui.session_state["records"], self.RECORDS)
        self.assertEqual(ui.session_state["predictions"], stored_predictions)
        store.list_indicators.assert_called_once_with(period="primer_parcial")
        store.list_predictions.assert_called_once_with(period="primer_parcial")
        app.show_tutor(ui, store)
        store.list_indicators.assert_called_once()
        store.list_predictions.assert_called_once()

    def test_tutor_preserves_current_session_without_overwriting_from_database(self):
        ui = FakeUI(role="Tutor")
        ui.session_state["records"] = self.RECORDS.copy()
        store = self.store()
        app.show_tutor(ui, store)
        store.list_indicators.assert_not_called()
        store.list_predictions.assert_not_called()

    def test_student_request_retains_existing_store_contract(self):
        ui = FakeUI(role="Estudiante")
        ui.buttons = {"Enviar solicitud"}
        ui.text = {"Identificador del estudiante": "EST-001", "¿En qué necesitas apoyo?": "Duda ficticia"}
        store = self.store()
        app.show_student(ui, store)
        store.create_request.assert_called_once_with("EST-001", "Duda ficticia")
        ui.buttons.clear()
        app.show_student(ui, store)
        self.assertIn(("success", "Solicitud 7 registrada. El tutor podrá revisarla."), ui.messages)

    def test_student_sqlite_failure_is_reported(self):
        ui = FakeUI(role="Estudiante")
        ui.buttons = {"Enviar solicitud"}
        store = self.store()
        store.create_request.side_effect = app.DatabaseError("SQLite sin conexión")
        app.show_student(ui, store)
        self.assertIn(("error", "SQLite sin conexión"), ui.messages)

    def test_support_and_followup_retain_existing_store_contract(self):
        ui = FakeUI(role="Tutor")
        ui.buttons = {"Registrar apoyo", "Guardar seguimiento"}
        ui.text = {"Identificador del estudiante": "EST-001", "Acuerdo de apoyo ficticio": "Acuerdo ficticio", "Nota ficticia de seguimiento": "Seguimiento ficticio"}
        store = self.store()
        store.list_supports.return_value = [{"id": 9, "student_id": "EST-001", "support_type": app.SUPPORT_TYPES[0], "status": "Pendiente"}]
        app.show_tutor(ui, store)
        store.create_support.assert_called_once_with("EST-001", app.SUPPORT_TYPES[0], "Acuerdo ficticio")
        store.add_followup.assert_called_once_with(9, "Seguimiento ficticio", "Pendiente")
        store.list_followups.assert_called_once_with(9)
        self.assertEqual(ui.reruns, 2)


if __name__ == "__main__":
    unittest.main()
