"""Contratos de MySQLStore; pruebas unitarias sin servidor ni credenciales."""

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import os
import sys
import threading
import unittest
from unittest.mock import MagicMock, Mock, patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from messi.data import ValidationError
from messi.database import DatabaseError, MySQLConfig, MySQLDatabase
from messi.mysql_storage import MySQLStore


def indicator(student="EST-001", grade=6.5):
    return {"id_estudiante": student, "nota_parcial": grade, "asistencia": 80.0, "tareas_entregadas": 70.0}


def prediction(student="EST-001", grade=6.5):
    return {**indicator(student, grade), "puntuacion_riesgo": 0.65, "alerta": True, "origen_modelo": "demo_sintetica"}


def cursor(row=None, rows=None, lastrowid=0, rowcount=1):
    result = Mock(lastrowid=lastrowid, rowcount=rowcount)
    result.fetchone.return_value = row
    result.fetchall.return_value = rows if rows is not None else []
    return result


class MySQLStoreTests(unittest.TestCase):
    def setUp(self):
        self.config = object()
        self.database = MagicMock()
        self.connection = self.database.connection.return_value.__enter__.return_value
        self.connection.execute.return_value = cursor()
        self.factory = patch("messi.mysql_storage.MySQLDatabase", return_value=self.database)
        self.factory_mock = self.factory.start()
        self.addCleanup(self.factory.stop)
        self.store = MySQLStore(self.config)

    def tearDown(self):
        # Las entradas siempre se envían aparte del SQL, con placeholders MySQL.
        for call in self.connection.execute.call_args_list:
            sql = call.args[0]
            params = call.args[1] if len(call.args) > 1 else ()
            self.assertNotIn("?", sql)
            self.assertEqual(sql.count("%s"), len(params))

    def test_construction_is_lazy_and_uses_supplied_config(self):
        self.factory_mock.assert_called_once_with(self.config)
        self.database.connection.assert_not_called()

    def test_request_registers_student_and_preserves_sql_like_text(self):
        payload = "Robert'); DROP TABLE supports; --"
        self.connection.execute.side_effect = [cursor(rowcount=0), cursor(lastrowid=41)]
        self.assertEqual(self.store.create_request(" EST-001 ", " " + payload + " "), 41)
        calls = self.connection.execute.call_args_list
        self.assertIn("INSERT INTO students", calls[0].args[0])
        self.assertEqual(calls[0].args[1][0], "EST-001")
        self.assertIn("INSERT INTO requests", calls[1].args[0])
        self.assertNotIn(payload, calls[1].args[0])
        self.assertEqual(calls[1].args[1][:2], ("EST-001", payload))
        self.database.connection.assert_called_once_with()

    def test_support_has_default_status_and_same_validation_contract(self):
        self.connection.execute.side_effect = [cursor(), cursor(lastrowid=12)]
        self.assertEqual(self.store.create_support("EST-001", " Tutoria ", " Nota "), 12)
        params = self.connection.execute.call_args.args[1]
        self.assertEqual(params[:3], ("EST-001", "Tutoria", "Nota"))
        self.assertEqual(params[-1], "Pendiente")

    def test_invalid_ids_content_and_choices_fail_before_opening_connection(self):
        invalid_operations = (
            lambda: self.store.create_request("Ana", "Mensaje"),
            lambda: self.store.create_request("EST-001", ""),
            lambda: self.store.create_request("EST-001", "x" * 1001),
            lambda: self.store.create_support("EST-001", "Otro", "Nota"),
            lambda: self.store.add_followup(True, "Nota", "Cerrado"),
            lambda: self.store.add_followup(1, "Nota", "Otro"),
            lambda: self.store.list_requests("EST-001' OR 1=1 --"),
            lambda: self.store.list_supports("EST-12"),
            lambda: self.store.list_followups(0),
        )
        for operation in invalid_operations:
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                operation()
        self.database.connection.assert_not_called()

    def test_followup_accepts_unchanged_status_with_zero_update_rowcount(self):
        self.connection.execute.side_effect = [cursor(row={"id": 7}), cursor(rowcount=0), cursor(lastrowid=18)]
        self.assertEqual(self.store.add_followup(7, "Continúa pendiente", "Pendiente"), 18)
        calls = self.connection.execute.call_args_list
        self.assertIn("FOR UPDATE", calls[0].args[0])
        self.assertEqual(calls[0].args[1], (7,))
        self.assertIn("INSERT INTO followups", calls[-1].args[0])
        self.assertEqual(calls[-1].args[1][:3], (7, "Continúa pendiente", "Pendiente"))

    def test_unknown_support_cannot_be_updated_or_get_followup(self):
        self.connection.execute.return_value = cursor(row=None)
        with self.assertRaisesRegex(ValueError, "no existe"):
            self.store.add_followup(99, "Nota", "Cerrado")
        self.assertEqual(self.connection.execute.call_count, 1)
        self.assertIs(self.database.connection.return_value.__exit__.call_args.args[0], ValueError)

    def test_insert_failure_reaches_transaction_context_for_rollback(self):
        self.connection.execute.side_effect = [cursor(row={"id": 7}), cursor(), RuntimeError("fallo simulado")]
        with self.assertRaisesRegex(RuntimeError, "fallo simulado"):
            self.store.add_followup(7, "No conservar el cambio de estado", "Cerrado")
        self.assertIs(self.database.connection.return_value.__exit__.call_args.args[0], RuntimeError)

    def test_support_queries_filter_with_parameters_and_keep_descending_order(self):
        expected = [{"id": 2, "student_id": "EST-001"}, {"id": 1, "student_id": "EST-001"}]
        self.connection.execute.return_value = cursor(rows=expected)
        for method in (self.store.list_requests, self.store.list_supports):
            self.assertEqual(method("EST-001"), expected)
            self.assertIn("ORDER BY id DESC", self.connection.execute.call_args.args[0])
            self.assertEqual(self.connection.execute.call_args.args[1], ("EST-001",))
        self.assertEqual(self.store.list_followups(10), expected)
        self.assertEqual(self.connection.execute.call_args.args[1], (10,))

    def test_indicator_save_validates_entire_batch_before_connection(self):
        for records in ([], [indicator(), indicator()], [indicator(), indicator("EST-002", 11)], [{**indicator(), "nombre": "Ana"}]):
            with self.subTest(records=records), self.assertRaises(ValidationError):
                self.store.save_indicators(records)
        self.database.connection.assert_not_called()

    def test_period_is_nonempty_and_at_most_64_characters(self):
        for period in ("", "   ", "x" * 65, None, 7):
            for operation in (
                lambda: self.store.save_indicators([indicator()], period),
                lambda: self.store.list_indicators(period),
                lambda: self.store.save_predictions([prediction()], period),
                lambda: self.store.list_predictions(period),
            ):
                with self.subTest(period=period), self.assertRaises(ValueError):
                    operation()
        self.database.connection.assert_not_called()

    def test_indicator_change_removes_old_prediction_within_same_transaction(self):
        old = {"id": 50, **{key: value for key, value in indicator(grade=5).items() if key != "id_estudiante"}}
        self.connection.execute.side_effect = [cursor(), cursor(row=old), cursor(), cursor(lastrowid=50)]
        self.assertEqual(self.store.save_indicators([indicator()], "segundo_parcial"), 1)
        calls = self.connection.execute.call_args_list
        self.assertIn("FOR UPDATE", calls[1].args[0])
        self.assertEqual(calls[1].args[1], ("EST-001", "segundo_parcial"))
        self.assertIn("DELETE FROM predictions", calls[2].args[0])
        self.assertEqual(calls[2].args[1], (50,))
        self.assertIn("ON DUPLICATE KEY UPDATE", calls[3].args[0])
        self.database.connection.assert_called_once_with()

    def test_unchanged_indicators_keep_existing_prediction(self):
        old = {"id": 50, **{key: value for key, value in indicator().items() if key != "id_estudiante"}}
        self.connection.execute.side_effect = [cursor(), cursor(row=old), cursor()]
        self.store.save_indicators([indicator()])
        self.assertFalse(any("DELETE FROM predictions" in call.args[0] for call in self.connection.execute.call_args_list))

    def test_batch_locks_students_in_stable_order(self):
        self.connection.execute.return_value = cursor(row=None)
        self.store.save_indicators([indicator("EST-003"), indicator("EST-001"), indicator("EST-002")])
        locked_ids = [call.args[1][0] for call in self.connection.execute.call_args_list if "INSERT INTO students" in call.args[0]]
        self.assertEqual(locked_ids, ["EST-001", "EST-002", "EST-003"])

    def test_list_indicators_returns_canonical_fields_for_requested_period(self):
        self.connection.execute.return_value = cursor(rows=[indicator()])
        self.assertEqual(self.store.list_indicators(" primer_parcial "), [indicator()])
        sql, params = self.connection.execute.call_args.args
        self.assertIn("ORDER BY student_id", sql)
        self.assertEqual(params, ("primer_parcial",))

    def test_prediction_metadata_is_validated_before_connection(self):
        variants = (
            {"puntuacion_riesgo": float("nan")}, {"puntuacion_riesgo": float("inf")},
            {"puntuacion_riesgo": -0.1}, {"puntuacion_riesgo": 1.1}, {"puntuacion_riesgo": True},
            {"puntuacion_riesgo": None}, {"alerta": 1}, {"alerta": "true"},
            {"origen_modelo": ""}, {"origen_modelo": "x" * 101}, {"nombre": "Ana"},
            {"asistencia": 101},
        )
        for variant in variants:
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                self.store.save_predictions([{**prediction(), **variant}])
        missing = prediction()
        del missing["alerta"]
        with self.assertRaises(ValueError):
            self.store.save_predictions([missing])
        self.database.connection.assert_not_called()

    def test_prediction_does_not_overwrite_existing_snapshot(self):
        old = {"id": 50, **{key: value for key, value in indicator().items() if key != "id_estudiante"}}
        self.connection.execute.side_effect = [cursor(), cursor(row=old), cursor()]
        self.assertEqual(self.store.save_predictions([prediction()]), 1)
        calls = self.connection.execute.call_args_list
        self.assertIn("FOR UPDATE", calls[1].args[0])
        self.assertIn("INSERT INTO predictions", calls[2].args[0])
        self.assertEqual(calls[2].args[1][:4], (50, 0.65, 1, "demo_sintetica"))
        self.assertFalse(any("INSERT INTO indicators" in call.args[0] or "UPDATE indicators" in call.args[0] for call in calls))

    def test_prediction_creates_snapshot_when_no_indicator_exists(self):
        self.connection.execute.side_effect = [cursor(), cursor(row=None), cursor(lastrowid=50), cursor()]
        self.assertEqual(self.store.save_predictions([prediction()]), 1)
        calls = self.connection.execute.call_args_list
        self.assertIn("INSERT INTO indicators", calls[2].args[0])
        self.assertEqual(calls[3].args[1][0], 50)

    def test_stale_prediction_rejects_batch_without_updating_new_indicators(self):
        current = {"id": 50, **{key: value for key, value in indicator(grade=9).items() if key != "id_estudiante"}}
        self.connection.execute.side_effect = [cursor(), cursor(row=current)]
        with self.assertRaisesRegex(ValidationError, "cambiaron"):
            self.store.save_predictions([prediction(grade=6.5)])
        self.assertEqual(self.connection.execute.call_count, 2)
        self.assertIs(self.database.connection.return_value.__exit__.call_args.args[0], ValidationError)

    def test_later_stale_prediction_rolls_back_earlier_batch_write(self):
        first = {"id": 50, **{key: value for key, value in indicator().items() if key != "id_estudiante"}}
        second = {"id": 51, **{key: value for key, value in indicator(grade=9).items() if key != "id_estudiante"}}
        self.connection.execute.side_effect = [cursor(), cursor(row=first), cursor(), cursor(), cursor(row=second)]
        with self.assertRaises(ValidationError):
            self.store.save_predictions([prediction(), prediction("EST-002")])
        self.assertIs(self.database.connection.return_value.__exit__.call_args.args[0], ValidationError)
        self.database.connection.assert_called_once_with()

    def test_prediction_join_restores_score_records_contract(self):
        self.connection.execute.return_value = cursor(rows=[{**prediction(), "alerta": 1}])
        restored = self.store.list_predictions("segundo_parcial")
        self.assertEqual(restored, [prediction()])
        self.assertIs(restored[0]["alerta"], True)
        sql, params = self.connection.execute.call_args.args
        self.assertIn("JOIN indicators", sql)
        self.assertEqual(params, ("segundo_parcial",))


@unittest.skipUnless(os.environ.get("MESSI_TEST_MYSQL") == "1", "Integración MySQL opt-in: MESSI_TEST_MYSQL=1")
class MySQLStoreIntegrationTests(unittest.TestCase):
    """Servidor real, exclusivamente en una base cuyo nombre termina en _test.

    Se usan las variables MESSI_MYSQL_*; cada caso reserva IDs nuevos y elimina
    sólo sus propias filas. No se borran bases ni datos que existieran antes.
    """

    @classmethod
    def setUpClass(cls):
        cls.config = MySQLConfig.from_environment(ROOT)
        if not cls.config.database.endswith("_test"):
            raise RuntimeError("Las pruebas de integración requieren una base aislada con sufijo _test.")
        cls.database = MySQLDatabase(cls.config)
        cls.database.initialize(create_database=True)

    def setUp(self):
        self.ids = []
        self.addCleanup(self.cleanup_owned_rows)
        self.store = MySQLStore(self.config)
        self.period = "test_" + uuid.uuid4().hex
        with self.database.connection() as connection:
            while len(self.ids) < 3:
                student_id = f"EST-{10_000_000 + uuid.uuid4().int % 90_000_000}"
                if connection.execute("SELECT id FROM students WHERE id = %s", (student_id,)).fetchone() is None:
                    connection.execute("INSERT INTO students(id, created_at) VALUES (%s, %s)", (student_id, "2026-10-03T00:00:00+00:00"))
                    self.ids.append(student_id)

    def cleanup_owned_rows(self):
        if not self.ids:
            return
        placeholders = ", ".join("%s" for _ in self.ids)
        params = tuple(self.ids)
        with self.database.connection() as connection:
            connection.execute(
                f"DELETE FROM followups WHERE support_id IN (SELECT id FROM supports WHERE student_id IN ({placeholders}))", params,
            )
            connection.execute(
                f"DELETE FROM predictions WHERE indicator_id IN (SELECT id FROM indicators WHERE student_id IN ({placeholders}))", params,
            )
            for table in ("requests", "supports", "indicators"):
                connection.execute(f"DELETE FROM {table} WHERE student_id IN ({placeholders})", params)
            connection.execute(f"DELETE FROM students WHERE id IN ({placeholders})", params)

    def test_support_records_survive_reopening_and_repeated_status(self):
        student = self.ids[0]
        payload = "Información: Robert'); DROP TABLE supports; --"
        request_id = self.store.create_request(student, payload)
        support_id = self.store.create_support(student, "Tutoria", "Plan de apoyo")
        first = self.store.add_followup(support_id, "Primer seguimiento", "Pendiente")
        second = self.store.add_followup(support_id, "Segundo seguimiento", "Pendiente")
        reopened = MySQLStore(self.config)
        self.assertEqual(reopened.list_requests(student)[0]["id"], request_id)
        self.assertEqual(reopened.list_requests(student)[0]["message"], payload)
        self.assertEqual(reopened.list_supports(student)[0]["status"], "Pendiente")
        self.assertEqual([row["id"] for row in reopened.list_followups(support_id)], [second, first])

    def test_indicator_updates_preserve_or_invalidate_prediction_and_separate_periods(self):
        student = self.ids[0]
        original = indicator(student)
        self.store.save_indicators([original], self.period)
        self.store.save_predictions([prediction(student)], self.period)
        self.store.save_indicators([original], self.period)
        self.assertEqual(self.store.list_predictions(self.period), [prediction(student)])
        changed = indicator(student, 9)
        self.store.save_indicators([changed], self.period)
        self.assertEqual(self.store.list_predictions(self.period), [])
        self.assertEqual(self.store.list_indicators(self.period), [changed])
        self.store.save_predictions([prediction(student)], self.period + "_other")
        self.assertEqual(self.store.list_predictions(self.period + "_other"), [prediction(student)])
        self.assertEqual(self.store.list_indicators(self.period), [changed])

    def test_stale_prediction_rolls_back_entire_batch_and_retains_changed_indicators(self):
        first, second = sorted(self.ids[:2])
        prior_prediction = {**prediction(first), "puntuacion_riesgo": 0.2, "alerta": False}
        self.store.save_predictions([prior_prediction], self.period)
        self.store.save_indicators([indicator(second, 9)], self.period)
        with self.assertRaises(ValidationError):
            self.store.save_predictions([prediction(first), prediction(second)], self.period)
        self.assertEqual(self.store.list_predictions(self.period), [prior_prediction])
        expected = sorted([indicator(first), indicator(second, 9)], key=lambda row: row["id_estudiante"])
        self.assertEqual(self.store.list_indicators(self.period), expected)

    def test_foreign_key_failure_rolls_back_support_status(self):
        support_id = self.store.create_support(self.ids[0], "Tutoria", "Pendiente")
        with self.assertRaises(DatabaseError):
            with self.database.connection() as connection:
                self.assertIsNone(connection.execute("SELECT id FROM supports WHERE id = %s", (0,)).fetchone())
                connection.execute("UPDATE supports SET status = %s WHERE id = %s", ("Cerrado", support_id))
                connection.execute(
                    "INSERT INTO followups(support_id, notes, status, created_at) VALUES (%s, %s, %s, %s)",
                    (0, "Sin apoyo", "Cerrado", "2026-10-03T00:00:00+00:00"),
                )
        self.assertEqual(self.store.list_supports(self.ids[0])[0]["status"], "Pendiente")
        self.assertEqual(self.store.list_followups(support_id), [])

    def test_concurrent_indicator_change_never_keeps_prediction_of_old_values(self):
        student = self.ids[0]
        self.store.save_indicators([indicator(student)], self.period)
        barrier = threading.Barrier(2)

        def update_indicators():
            barrier.wait(timeout=10)
            self.store.save_indicators([indicator(student, 9)], self.period)

        def persist_old_prediction():
            barrier.wait(timeout=10)
            try:
                self.store.save_predictions([prediction(student)], self.period)
            except ValidationError:
                pass  # Si el cambio se confirmó primero, este cálculo ya no aplica.

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(update_indicators), pool.submit(persist_old_prediction)]
            for future in futures:
                future.result(timeout=25)
        self.assertEqual(self.store.list_indicators(self.period), [indicator(student, 9)])
        self.assertEqual(self.store.list_predictions(self.period), [])


if __name__ == "__main__":
    unittest.main()
