"""Migración de un SQLite temporal real; destino simulado y MySQL opt-in."""
from contextlib import closing, contextmanager
from copy import deepcopy
from dataclasses import replace
import os
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from messi.database import DatabaseError, MySQLConfig, MySQLDatabase
from messi.migration import MigrationError, migrate_sqlite
from messi.mysql_storage import MySQLStore
from messi.storage import SupportStore


def make_source(root):
    source = Path(root) / "messi.sqlite3"
    store = SupportStore(source)
    discarded_request = store.create_request("EST-001", "Fila temporal")
    discarded_support = store.create_support("EST-001", "Tutoria", "Fila temporal")
    with closing(sqlite3.connect(source)) as db, db:
        db.execute("DELETE FROM requests WHERE id = ?", (discarded_request,))
        db.execute("DELETE FROM supports WHERE id = ?", (discarded_support,))
    store.create_request("EST-001", "Duda de matemáticas: Robert'); DROP TABLE supports; --")
    store.create_request("EST-002", "Otro mensaje ficticio")
    support = store.create_support("EST-001", "Tutoria", "Acuerdo ficticio con acentos: información")
    store.add_followup(support, "Primer seguimiento", "En seguimiento")
    store.add_followup(support, "Segundo seguimiento", "Cerrado")
    expected = {
        "requests": sorted(store.list_requests(), key=lambda row: row["id"]),
        "supports": sorted(store.list_supports(), key=lambda row: row["id"]),
        "followups": sorted(store.list_followups(support), key=lambda row: row["id"]),
    }
    return source, expected


class FakeCursor:
    def __init__(self, rows=()):
        self.rows = list(rows)

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows.copy()


class FakeMySQLDatabase:
    """Destino con rollback real del estado y las sentencias de la importación."""
    def __init__(self):
        self.tables = {name: [] for name in ("students", "requests", "supports", "followups")}
        self.tables["schema_migrations"] = [{"version": 1}]
        self.connections = self.commits = self.rollbacks = 0
        self.statements = []
        self.fail_on_table = None

    @contextmanager
    def connection(self):
        self.connections += 1
        previous = deepcopy(self.tables)
        try:
            yield self
        except BaseException:
            self.tables = previous
            self.rollbacks += 1
            raise
        else:
            self.commits += 1

    def execute(self, sql, params=()):
        self.statements.append((sql, params))
        if sql.startswith("SELECT version FROM schema_migrations"):
            return FakeCursor([row for row in self.tables["schema_migrations"] if row["version"] == params[0]])
        if sql.startswith("SELECT id FROM"):
            table = sql.split()[3]
            return FakeCursor([{"id": row["id"]} for row in self.tables[table]])
        inserted = re.match(r"INSERT INTO (\w+)\(([^)]+)\)", sql)
        if not inserted:
            raise AssertionError(f"Unexpected migration SQL: {sql}")
        table, columns = inserted.groups()
        if self.fail_on_table == table:
            raise DatabaseError("Fallo simulado de escritura MySQL")
        row = dict(zip([column.strip() for column in columns.split(",")], params, strict=True))
        if table == "students" and any(student["id"] == row["id"] for student in self.tables[table]):
            return FakeCursor()
        self.tables[table].append(row)
        return FakeCursor()


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.root = Path(self.temporal.name)
        self.source, self.expected = make_source(self.root)
        self.original = self.source.read_bytes()
        self.modified_time = self.source.stat().st_mtime_ns
        self.database = FakeMySQLDatabase()

    def assert_source_intact(self):
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(self.source.stat().st_mtime_ns, self.modified_time)

    def test_source_read_only_and_ids_content_links_are_preserved(self):
        original_connect = sqlite3.connect
        with patch("messi.migration.sqlite3.connect", wraps=original_connect) as connect:
            result = migrate_sqlite(self.source, self.database)
        connect.assert_called_once_with(self.source.resolve().as_uri() + "?mode=ro", uri=True)
        self.assertEqual(result, {table: len(rows) for table, rows in self.expected.items()})
        for table, rows in self.expected.items():
            self.assertEqual(self.database.tables[table], rows)
        self.assertEqual([row["id"] for row in self.database.tables["students"]], ["EST-001", "EST-002"])
        self.assertEqual(self.database.tables["followups"][0]["support_id"], self.expected["supports"][0]["id"])
        self.assertEqual(self.database.commits, 1)
        self.assertEqual(self.database.rollbacks, 0)
        marker = self.database.tables["schema_migrations"][-1]
        self.assertEqual(marker["version"], 2)
        self.assert_source_intact()
        for sql, params in self.database.statements:
            self.assertEqual(sql.count("%s"), len(params))
            self.assertNotIn("Robert", sql)
        locked_tables = {sql.split()[3] for sql, _ in self.database.statements
                         if sql.startswith("SELECT id FROM") and "FOR UPDATE" in sql}
        self.assertEqual(locked_tables, {"requests", "supports", "followups"})

    def test_marker_two_prevents_duplicate_imports(self):
        migrate_sqlite(self.source, self.database)
        previous = deepcopy(self.database.tables)
        self.assertEqual(migrate_sqlite(self.source, self.database), {"already_applied": True})
        self.assertEqual(self.database.tables, previous)
        self.assert_source_intact()

    def test_any_nonempty_destination_table_rejects_import(self):
        for table in ("requests", "supports", "followups"):
            with self.subTest(table=table):
                target = FakeMySQLDatabase()
                target.tables[table] = [{"id": 999}]
                previous = deepcopy(target.tables)
                with self.assertRaisesRegex(MigrationError, "vacíos"):
                    migrate_sqlite(self.source, target)
                self.assertEqual(target.tables, previous)
                self.assertEqual(target.commits, 0)
                self.assertEqual(target.rollbacks, 1)
        self.assert_source_intact()

    def test_late_mysql_failure_rolls_back_all_imported_rows_and_marker(self):
        self.database.fail_on_table = "followups"
        previous = deepcopy(self.database.tables)
        with self.assertRaises(DatabaseError):
            migrate_sqlite(self.source, self.database)
        self.assertEqual(self.database.tables, previous)
        self.assertEqual(self.database.rollbacks, 1)
        self.assertEqual(self.database.commits, 0)
        self.assertTrue(any("INSERT INTO supports" in sql for sql, _ in self.database.statements))
        self.assert_source_intact()

    def test_abril_schema_is_rejected_before_destination_is_opened(self):
        unrelated = self.root / "abril.db"
        with closing(sqlite3.connect(unrelated)) as db, db:
            db.execute("CREATE TABLE recuerdos(id INTEGER PRIMARY KEY, contenido TEXT)")
            db.execute("CREATE TABLE recetas(id INTEGER PRIMARY KEY, nombre TEXT)")
        original = unrelated.read_bytes()
        with self.assertRaisesRegex(MigrationError, "MESSI"):
            migrate_sqlite(unrelated, self.database)
        self.assertEqual(unrelated.read_bytes(), original)
        self.assertEqual(self.database.connections, 0)

    def test_corrupt_file_is_rejected_without_creating_destination_data(self):
        corrupt = self.root / "corrupt.sqlite3"
        corrupt.write_bytes(b"not a SQLite database")
        with self.assertRaises(MigrationError):
            migrate_sqlite(corrupt, self.database)
        self.assertEqual(corrupt.read_bytes(), b"not a SQLite database")
        self.assertEqual(self.database.connections, 0)

    def test_orphan_followup_is_rejected_without_touching_destination(self):
        with closing(sqlite3.connect(self.source)) as db, db:
            db.execute("PRAGMA foreign_keys = OFF")
            db.execute("INSERT INTO followups(support_id, notes, status, created_at) VALUES (?, ?, ?, ?)",
                       (999, "Sin apoyo", "Pendiente", "2026-10-03T12:00:00+00:00"))
        original = self.source.read_bytes()
        with self.assertRaises(MigrationError):
            migrate_sqlite(self.source, self.database)
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(self.database.connections, 0)

    def test_invalid_saved_date_is_rejected_before_destination_is_opened(self):
        with closing(sqlite3.connect(self.source)) as db, db:
            db.execute("UPDATE requests SET created_at = ?", ("invalid-date",))
        original = self.source.read_bytes()
        with self.assertRaises(MigrationError):
            migrate_sqlite(self.source, self.database)
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(self.database.connections, 0)

    def test_missing_source_does_not_create_a_sqlite_file(self):
        missing = self.root / "does-not-exist.sqlite3"
        with self.assertRaises(MigrationError):
            migrate_sqlite(missing, self.database)
        self.assertFalse(missing.exists())
        self.assertEqual(self.database.connections, 0)


@unittest.skipUnless(os.environ.get("MESSI_TEST_MYSQL") == "1", "MySQL opt-in: MESSI_TEST_MYSQL=1")
class MigrationMySQLIntegrationTests(unittest.TestCase):
    """Destino exclusivo *_migration_test; sin DROP y sin limpiar filas ajenas."""
    def test_exact_sqlite_migration_and_idempotence_on_empty_mysql_database(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        # Lee únicamente variables de proceso; nunca el .env de la instalación.
        config = MySQLConfig.from_environment(Path(temporary.name))
        if not config.database.endswith("_test"):
            raise RuntimeError("La integración exige una base configurada con sufijo _test.")
        migration_config = replace(config, database=config.database + "_migration_test")
        target = MySQLDatabase(migration_config)
        target.initialize(create_database=True)
        with target.connection() as db:
            for table in ("students", "requests", "supports", "followups", "indicators", "predictions"):
                if db.execute(f"SELECT COUNT(*) AS total FROM {table}").fetchone()["total"]:
                    raise RuntimeError("El destino de migración debe estar vacío; no se modificarán sus datos.")
            if db.execute("SELECT version FROM schema_migrations WHERE version = %s", (2,)).fetchone():
                raise RuntimeError("El destino ya contiene una migración anterior; no se modificará.")
        source, expected = make_source(temporary.name)
        original = source.read_bytes()
        student_ids = sorted({row["student_id"] for table in ("requests", "supports") for row in expected[table]})

        def cleanup_owned_rows():
            with target.connection() as db:
                for table in ("followups", "supports", "requests"):
                    for row in expected[table]:
                        db.execute(f"DELETE FROM {table} WHERE id = %s", (row["id"],))
                for student in student_ids:
                    db.execute("DELETE FROM students WHERE id = %s", (student,))
                db.execute("DELETE FROM schema_migrations WHERE version = %s AND description = %s",
                           (2, "Importación de SQLite MESSI"))
        self.addCleanup(cleanup_owned_rows)
        self.assertEqual(migrate_sqlite(source, target), {table: len(rows) for table, rows in expected.items()})
        reopened = MySQLStore(migration_config)
        self.assertEqual(sorted(reopened.list_requests(), key=lambda row: row["id"]), expected["requests"])
        self.assertEqual(sorted(reopened.list_supports(), key=lambda row: row["id"]), expected["supports"])
        for support in expected["supports"]:
            self.assertEqual(sorted(reopened.list_followups(support["id"]), key=lambda row: row["id"]),
                             [row for row in expected["followups"] if row["support_id"] == support["id"]])
        self.assertEqual(migrate_sqlite(source, target), {"already_applied": True})
        self.assertEqual(source.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
