"""Pruebas de persistencia ejecutables con unittest y una base temporal."""

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import tempfile
import unittest

from messi.storage import SUPPORT_STATUSES, SUPPORT_TYPES, SupportStore


class SupportStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "private" / "messi.sqlite3"
        self.store = SupportStore(self.path)

    def test_requests_and_supports_survive_reopening(self):
        request_id = self.store.create_request("EST-001", "Necesito orientación.")
        support_id = self.store.create_support("EST-001", "Tutoria", "Plan de ejemplo.")
        followup_id = self.store.add_followup(support_id, "Sesión realizada.", "En seguimiento")
        reopened = SupportStore(self.path)
        request = reopened.list_requests()[0]
        support = reopened.list_supports()[0]
        followup = reopened.list_followups(support_id)[0]
        self.assertEqual(request["id"], request_id)
        self.assertEqual(request["message"], "Necesito orientación.")
        self.assertEqual(support["id"], support_id)
        self.assertEqual(support["status"], "En seguimiento")
        self.assertEqual(followup["id"], followup_id)
        self.assertEqual(followup["support_id"], support_id)
        self.assertEqual(followup["notes"], "Sesión realizada.")
        for record in (request, support, followup):
            self.assertEqual(datetime.fromisoformat(record["created_at"]).tzinfo, timezone.utc)

    def test_request_needs_no_csv_or_prediction(self):
        request_id = self.store.create_request("EST-003", "Solicito apoyo accesible.")
        self.assertEqual(self.store.list_requests("EST-003")[0]["id"], request_id)
        self.assertEqual(self.store.list_supports(), [])

    def test_filtering_and_newest_first_order(self):
        first = self.store.create_request("EST-001", "Primera solicitud.")
        self.store.create_request("EST-002", "Otra persona.")
        latest = self.store.create_request("EST-001", "Segunda solicitud.")
        self.assertEqual([r["id"] for r in self.store.list_requests("EST-001")], [latest, first])
        support = self.store.create_support("EST-001", "Tutoria", "Ejemplo.")
        other = self.store.create_support("EST-002", "Orientacion", "Otro ejemplo.")
        self.assertEqual([r["id"] for r in self.store.list_supports("EST-001")], [support])
        self.assertEqual([r["id"] for r in self.store.list_supports()], [other, support])
        self.store.add_followup(other, "Otra persona atendida.", "Cerrado")
        first_followup = self.store.add_followup(support, "Primer avance.", "En seguimiento")
        latest_followup = self.store.add_followup(support, "Objetivo cumplido.", "Cerrado")
        self.assertEqual(
            [r["id"] for r in self.store.list_followups(support)],
            [latest_followup, first_followup],
        )
        self.assertEqual(self.store.list_requests("EST-999"), [])
        self.assertEqual(self.store.list_supports("EST-999"), [])

    def test_invalid_student_ids_are_rejected_for_writes_and_filters(self):
        for bad_id in ("", "EST-12", "EST-123456789", "est-123", "EST-１２３", "EST-001\nX", None, 123):
            for operation in (
                lambda: self.store.create_request(bad_id, "Mensaje."),
                lambda: self.store.create_support(bad_id, "Tutoria", "Nota."),
            ):
                with self.subTest(student_id=bad_id), self.assertRaises(ValueError):
                    operation()
            if bad_id is not None:  # None significa consultar todos los registros.
                with self.assertRaises(ValueError):
                    self.store.list_requests(bad_id)
                with self.assertRaises(ValueError):
                    self.store.list_supports(bad_id)
        for valid_id in ("EST-123", "EST-12345678"):
            self.store.create_request(valid_id, "Identificador válido.")

    def test_empty_non_text_and_oversized_content_is_rejected(self):
        support = self.store.create_support("EST-001", "Tutoria", "Nota válida.")
        for invalid in ("", " \n\t ", "x" * 1001, None, 123):
            for operation in (
                lambda: self.store.create_request("EST-001", invalid),
                lambda: self.store.create_support("EST-001", "Tutoria", invalid),
                lambda: self.store.add_followup(support, invalid, "Cerrado"),
            ):
                with self.subTest(content=invalid), self.assertRaises(ValueError):
                    operation()
        self.store.create_request(" EST-001 ", " " + "x" * 1000 + " ")
        self.assertEqual(len(self.store.list_requests()[0]["message"]), 1000)
        self.assertEqual(self.store.list_requests()[0]["student_id"], "EST-001")
        self.assertEqual(self.store.list_supports()[0]["status"], "Pendiente")

    def test_types_and_statuses_are_validated(self):
        for support_type in SUPPORT_TYPES:
            self.store.create_support("EST-001", support_type, "Nota de prueba.")
        support = self.store.list_supports()[0]["id"]
        for status in SUPPORT_STATUSES:
            self.store.add_followup(support, "Avance de prueba.", status)
            self.assertEqual(self.store.list_supports()[0]["status"], status)
        for invalid in ("", "Desconocido", None, "Tutoria'); DROP TABLE supports; --"):
            with self.assertRaises(ValueError):
                self.store.create_support("EST-001", invalid, "Nota.")
            with self.assertRaises(ValueError):
                self.store.add_followup(support, "Nota.", invalid)

    def test_unknown_or_invalid_support_cannot_create_followup(self):
        with self.assertRaisesRegex(ValueError, "no existe"):
            self.store.add_followup(999, "No debe guardarse.", "Cerrado")
        for invalid in (0, -1, True, "1", 1.0, None):
            with self.subTest(support_id=invalid), self.assertRaises(ValueError):
                self.store.add_followup(invalid, "Nota.", "Cerrado")
            with self.assertRaises(ValueError):
                self.store.list_followups(invalid)
        self.assertEqual(self.store.list_followups(999), [])

    def test_foreign_keys_are_enforced_on_store_connections(self):
        with self.store._connection() as connection:
            self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO followups(support_id, notes, status, created_at) VALUES (?, ?, ?, ?)",
                    (999, "Sin apoyo.", "Pendiente", "2026-10-03T00:00:00+00:00"),
                )

    def test_failure_rolls_back_both_followup_and_support_status(self):
        support = self.store.create_support("EST-001", "Tutoria", "Nota.")
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute(
                "CREATE TRIGGER reject_followup BEFORE INSERT ON followups "
                "BEGIN SELECT RAISE(ABORT, 'fallo simulado'); END"
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.add_followup(support, "No debe guardarse.", "Cerrado")
        self.assertEqual(self.store.list_supports()[0]["status"], "Pendiente")
        self.assertEqual(self.store.list_followups(support), [])

    def test_sql_like_text_is_stored_as_text(self):
        payload = "Robert'); DROP TABLE supports; --"
        self.store.create_request("EST-001", payload)
        support = self.store.create_support("EST-001", "Tutoria", payload)
        self.store.add_followup(support, payload, "Cerrado")
        self.assertEqual(self.store.list_requests()[0]["message"], payload)
        self.assertEqual(self.store.list_supports()[0]["notes"], payload)
        self.assertEqual(self.store.list_followups(support)[0]["notes"], payload)
        with self.assertRaises(ValueError):
            self.store.list_requests("EST-001' OR 1=1 --")
        self.assertEqual(len(self.store.list_supports()), 1)


if __name__ == "__main__":
    unittest.main()
