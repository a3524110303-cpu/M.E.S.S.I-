"""Regresiones de estado y rutas de la interfaz, sin abrir Streamlit.

La comprobación visual y las interacciones reales requieren Streamlit instalado.
"""

import contextlib
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch

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
        self.counts = False

    def radio(self, label, options, **kwargs):
        if label == "Vista de demostración":
            return self.role
        if label == "¿Cómo tienes la asistencia y las tareas?":
            return options[1 if self.counts else 0]
        return self.source

    def button(self, label, **kwargs):
        return label in self.buttons

    form_submit_button = button

    def form(self, *args, **kwargs):
        return contextlib.nullcontext()

    def number_input(self, label, **kwargs):
        return self.numeric.get(label)

    def text_input(self, label, **kwargs):
        return self.text.get(label, "")

    def text_area(self, label, **kwargs):
        return self.text.get(label, "")

    def file_uploader(self, *args, **kwargs):
        return None

    def error(self, message):
        self.messages.append(("error", message))

    def info(self, message):
        self.messages.append(("info", message))

    def __getattr__(self, name):
        if name in {"set_page_config", "title", "write", "warning", "caption", "header", "subheader", "download_button", "dataframe", "success"}:
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
        ui.session_state.update(input_source="Ejemplo sintético", records=[{"old": 1}], predictions=[{"old": 1}])
        app.show_teacher(ui)
        self.assertNotIn("records", ui.session_state)
        self.assertNotIn("predictions", ui.session_state)

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
        with patch.dict(sys.modules, {"streamlit": ui}), patch.object(app, "SupportStore", side_effect=sqlite3.OperationalError("locked")) as store:
            app.main()
        store.assert_not_called()
        self.assertFalse(any(kind == "error" for kind, _ in ui.messages))

    def test_invalid_manual_addition_preserves_captured_rows(self):
        ui = FakeUI(source="Captura directa")
        existing = [{"id_estudiante": "EST-0001", "nota_parcial": 6.0, "asistencia": 80.0, "tareas_entregadas": 70.0}]
        ui.session_state.update(input_source="Captura directa", records=existing)
        ui.buttons.add("Agregar estudiante")
        app.show_teacher(ui)  # Campos nuevos vacíos, sin perder la fila previa.
        self.assertEqual(ui.session_state["records"], existing)
        self.assertTrue(any(kind == "error" for kind, _ in ui.messages))

    def test_locked_storage_is_reported_to_tutor(self):
        ui = FakeUI(role="Tutor")
        with patch.dict(sys.modules, {"streamlit": ui}), patch.object(app, "SupportStore", side_effect=sqlite3.OperationalError("locked")):
            app.main()
        self.assertTrue(any(kind == "error" and "registro de apoyos" in message for kind, message in ui.messages))


if __name__ == "__main__":
    unittest.main()
