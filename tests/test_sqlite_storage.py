"""Contrato real de SQLite: lotes, vigencia de predicciones, respaldo y legado."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from messi.data import ValidationError
from messi.database import DatabaseError
from messi.storage import SupportStore
from messi.sqlite_storage import SQLiteStore


class SQLiteStorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "messi.sqlite3"
        self.store = SQLiteStore(self.path)
        self.records = [
            {"id_estudiante": "EST-001", "nota_parcial": 5.8, "asistencia": 70.0, "tareas_entregadas": 50.0},
            {"id_estudiante": "EST-002", "nota_parcial": 8.0, "asistencia": 90.0, "tareas_entregadas": 85.0},
        ]
        self.predictions = [{**row, "puntuacion_riesgo": risk, "alerta": risk >= 0.5, "origen_modelo": "demo_sintetica"}
                            for row, risk in zip(self.records, (0.75, 0.2))]

    def test_complete_flow_survives_reopening(self):
        self.store.save_indicators(self.records)
        self.store.save_predictions(self.predictions)
        request = self.store.create_request("EST-001", "Apoyo sin conexión a internet")
        support = self.store.create_support("EST-001", "Tutoria", "Acuerdo de prueba")
        self.store.add_followup(support, "Seguimiento", "Cerrado")
        reopened = SQLiteStore(self.path)
        self.assertEqual(reopened.list_indicators(), self.records)
        self.assertEqual(reopened.list_predictions(), self.predictions)
        self.assertEqual(reopened.list_requests()[0]["id"], request)
        self.assertEqual(reopened.list_supports()[0]["status"], "Cerrado")
        self.assertEqual(reopened.list_followups(support)[0]["notes"], "Seguimiento")

    def test_changed_indicators_invalidate_only_their_prediction(self):
        self.store.save_predictions(self.predictions)
        changed = {**self.records[0], "nota_parcial": 9.0}
        self.store.save_indicators([changed])
        self.assertEqual(self.store.list_predictions(), [self.predictions[1]])
        self.assertEqual(self.store.list_indicators(), [changed, self.records[1]])

    def test_same_indicators_preserve_prediction(self):
        self.store.save_predictions(self.predictions)
        self.store.save_indicators(self.records)
        self.assertEqual(self.store.list_predictions(), self.predictions)

    def test_stale_prediction_rolls_back_the_entire_batch(self):
        self.store.save_indicators([self.records[1]])
        stale = {**self.predictions[1], "nota_parcial": 9.0}
        with self.assertRaises(ValidationError):
            self.store.save_predictions([self.predictions[0], stale])
        self.assertEqual(self.store.list_predictions(), [])
        self.assertEqual(self.store.list_indicators(), [self.records[1]])

    def test_periods_do_not_overwrite_each_other(self):
        self.store.save_predictions(self.predictions)
        other = {**self.records[0], "nota_parcial": 7.0}
        self.store.save_indicators([other], "segundo_parcial")
        self.assertEqual(self.store.list_indicators("segundo_parcial"), [other])
        self.assertEqual(self.store.list_predictions(), self.predictions)

    def test_recalculation_updates_instead_of_duplicating(self):
        self.store.save_predictions(self.predictions)
        revised = [{**row, "puntuacion_riesgo": 0.4, "alerta": False} for row in self.predictions]
        self.store.save_predictions(revised)
        self.assertEqual(self.store.list_predictions(), revised)

    def test_invalid_prediction_never_persists_a_partial_batch(self):
        for change in ({"alerta": "sí"}, {"puntuacion_riesgo": float("nan")}, {"puntuacion_riesgo": 1.1}):
            with self.subTest(change=change):
                with self.assertRaises(ValidationError):
                    self.store.save_predictions([self.predictions[0], {**self.predictions[1], **change}])
                self.assertEqual(self.store.list_indicators(), [])

    def test_parallel_requests_are_all_committed(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            ids = list(pool.map(lambda i: self.store.create_request("EST-001", f"Solicitud {i}"), range(20)))
        self.assertEqual(len(set(ids)), 20)
        self.assertEqual(len(SQLiteStore(self.path).list_requests()), 20)

    def test_backup_includes_wal_changes_and_all_relationships(self):
        self.store.save_predictions(self.predictions)
        support = self.store.create_support("EST-001", "Tutoria", "Prueba")
        self.store.add_followup(support, "Nota", "En seguimiento")
        destination = Path(self.temporary.name) / "backup.sqlite3"
        self.store.backup(destination)
        copy = SQLiteStore(destination)
        self.assertEqual(copy.list_predictions(), self.predictions)
        self.assertEqual(copy.list_followups(support), self.store.list_followups(support))
        with copy._connection() as db:
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_cannot_backup_over_active_database(self):
        with self.assertRaises(ValueError):
            self.store.backup(self.path)

    def test_upgrade_keeps_legacy_ids_and_followups(self):
        path = Path(self.temporary.name) / "legacy.sqlite3"
        old = SupportStore(path)
        request = old.create_request("EST-003", "Solicitud anterior")
        support = old.create_support("EST-003", "Orientacion", "Apoyo anterior")
        old.add_followup(support, "Seguimiento anterior", "Cerrado")
        for _ in range(2):
            new = SQLiteStore(path)
            self.assertEqual(new.list_requests()[0]["id"], request)
            self.assertEqual(new.list_supports()[0]["id"], support)
            self.assertEqual(len(new.list_followups(support)), 1)

    def test_newer_database_is_rejected_without_modifying_its_schema(self):
        path = Path(self.temporary.name) / "future.sqlite3"
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("PRAGMA user_version=9")
        with self.assertRaises(DatabaseError):
            SQLiteStore(path)
        with closing(sqlite3.connect(path)) as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 9)
            self.assertEqual(db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(), [])

    def test_default_app_never_loads_mysql_configuration(self):
        import app
        from test_app import FakeUI
        ui = FakeUI(role="Tutor")
        with patch.dict(sys.modules, {"streamlit": ui}), \
                patch.object(app, "database_path", return_value=self.path), \
                patch("messi.database.MySQLConfig.from_environment", side_effect=AssertionError("No usar MySQL")):
            app.main()
        self.assertFalse(any(kind == "error" for kind, _ in ui.messages))


if __name__ == "__main__":
    unittest.main()
