"""Configuración, transacciones y DDL MySQL con un driver simulado."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from messi import database


class DriverError(Exception):
    def __init__(self, message="test-only-secret", errno=2013):
        super().__init__(message)
        self.errno = errno


def cursor(row=None):
    result = Mock()
    result.fetchone.return_value = row
    return result


class MySQLConfigTests(unittest.TestCase):
    def test_env_file_is_read_without_interpolating_password(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            root = Path(directory)
            (root / ".env").write_text(
                'MESSI_MYSQL_HOST=localhost\nMESSI_MYSQL_PORT=13307\n'
                'MESSI_MYSQL_USER=demo\nMESSI_MYSQL_PASSWORD="literal${NOT_DEFINED}"\n'
                'MESSI_MYSQL_DATABASE=messi_test\n', encoding="utf-8"
            )
            config = database.MySQLConfig.from_environment(root)
        self.assertEqual((config.host, config.port, config.user, config.database),
                         ("localhost", 13307, "demo", "messi_test"))
        self.assertEqual(config.password, "literal${NOT_DEFINED}")
        self.assertNotIn(config.password, repr(config))

    def test_process_environment_overrides_file_values(self):
        variables = {"MESSI_MYSQL_HOST": "127.0.0.1", "MESSI_MYSQL_PORT": "13308",
                     "MESSI_MYSQL_USER": "environment_user", "MESSI_MYSQL_PASSWORD": "environment_secret",
                     "MESSI_MYSQL_DATABASE": "environment_test"}
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, variables, clear=True):
            root = Path(directory)
            (root / ".env").write_text(
                "MESSI_MYSQL_HOST=filehost\nMESSI_MYSQL_PORT=13307\nMESSI_MYSQL_USER=fileuser\n"
                "MESSI_MYSQL_PASSWORD=file_secret\nMESSI_MYSQL_DATABASE=file_test\n", encoding="utf-8"
            )
            config = database.MySQLConfig.from_environment(root)
        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 13308)
        self.assertEqual(config.user, "environment_user")
        self.assertEqual(config.password, "environment_secret")
        self.assertEqual(config.database, "environment_test")
        self.assertNotIn("environment_secret", repr(config))

    def test_missing_configuration_reports_actionable_error(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(database.DatabaseError, ".env"):
                database.MySQLConfig.from_environment(Path(directory))

    def test_invalid_port_and_database_name_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for port in ("not-a-port", "0", "65536"):
                with self.subTest(port=port), patch.dict(os.environ, {
                    "MESSI_MYSQL_PASSWORD": "test-secret", "MESSI_MYSQL_PORT": port,
                }, clear=True), self.assertRaises(database.DatabaseError):
                    database.MySQLConfig.from_environment(Path(directory))
        for arguments in ({"database": "demo`; DROP DATABASE demo"}, {"port": True},
                          {"host": ""}, {"user": ""}, {"password": None}):
            with self.subTest(arguments=arguments), self.assertRaises(database.DatabaseError):
                database.MySQLConfig(**arguments)


class MySQLDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.config = database.MySQLConfig(password="test-only-secret", port=13307, database="unit_test")
        self.driver = SimpleNamespace(Error=DriverError, connect=Mock())
        self.driver_patch = patch.object(database, "_driver", return_value=self.driver)
        self.driver_patch.start()
        self.addCleanup(self.driver_patch.stop)
        self.db = database.MySQLDatabase(self.config)

    def test_constructor_is_lazy(self):
        self.driver.connect.assert_not_called()

    def test_open_uses_timeouts_utf8_and_disables_local_infile(self):
        raw = Mock()
        self.driver.connect.return_value = raw
        opened = self.db._open()
        self.assertIs(opened.raw, raw)
        arguments = self.driver.connect.call_args.kwargs
        self.assertEqual(arguments["database"], "unit_test")
        self.assertEqual(arguments["port"], 13307)
        self.assertEqual(arguments["charset"], "utf8mb4")
        self.assertFalse(arguments["autocommit"])
        self.assertFalse(arguments["allow_local_infile"])
        for key in ("connection_timeout", "read_timeout", "write_timeout"):
            self.assertGreater(arguments[key], 0)
        self.db._open(with_database=False)
        self.assertNotIn("database", self.driver.connect.call_args.kwargs)

    def test_open_errors_do_not_expose_driver_message_or_password(self):
        for errno in (1045, 1049, 1146, 1054, 2003, 2013, 9999):
            with self.subTest(errno=errno):
                self.driver.connect.side_effect = DriverError("test-only-secret private-host", errno)
                with self.assertRaises(database.DatabaseError) as raised:
                    self.db._open()
                self.assertNotIn("test-only-secret", str(raised.exception))
                self.assertNotIn("private-host", str(raised.exception))

    def test_dict_cursors_are_buffered_parameterized_and_closed(self):
        raw = Mock()
        first, second = Mock(), Mock()
        raw.cursor.side_effect = [first, second]
        db = database._Connection(raw)
        params = ("Robert'); DROP TABLE students; --",)
        self.assertIs(db.execute("SELECT id FROM students WHERE id=%s", params), first)
        self.assertIs(db.executemany("INSERT INTO students(id) VALUES (%s)", [params]), second)
        for call in raw.cursor.call_args_list:
            self.assertEqual(call.kwargs, {"dictionary": True, "buffered": True})
        first.execute.assert_called_once_with("SELECT id FROM students WHERE id=%s", params)
        second.executemany.assert_called_once_with("INSERT INTO students(id) VALUES (%s)", [params])
        db.close()
        first.close.assert_called_once()
        second.close.assert_called_once()
        raw.close.assert_called_once()

    def test_raw_connection_is_closed_when_cursor_close_fails(self):
        raw = Mock()
        raw.cursor.return_value.close.side_effect = RuntimeError("close failed")
        db = database._Connection(raw)
        db.execute("SELECT 1")
        with self.assertRaisesRegex(RuntimeError, "close failed"):
            db.close()
        raw.close.assert_called_once()

    def prepared_connection(self, *, marker=True):
        db = Mock(raw=Mock())
        db.execute.return_value = cursor({"version": 1} if marker else None)
        return db

    def test_successful_data_operation_commits_and_never_runs_ddl(self):
        opened = self.prepared_connection()
        with patch.object(self.db, "_open", return_value=opened):
            with self.db.connection() as connection:
                self.assertIs(connection, opened)
                connection.execute("INSERT INTO students(id, created_at) VALUES (%s, %s)",
                                   ("EST-001", "2026-10-03T00:00:00+00:00"))
        opened.raw.start_transaction.assert_called_once_with(isolation_level="REPEATABLE READ")
        opened.raw.rollback.assert_called_once_with()
        opened.raw.commit.assert_called_once_with()
        opened.close.assert_called_once_with()
        self.assertFalse(any(call.args[0].lstrip().upper().startswith(("CREATE ", "ALTER ", "DROP "))
                             for call in opened.execute.call_args_list))

    def test_application_failure_rolls_back_without_commit(self):
        opened = self.prepared_connection()
        failure = ValueError("Invalid operation")
        with patch.object(self.db, "_open", return_value=opened):
            with self.assertRaises(ValueError) as raised:
                with self.db.connection():
                    raise failure
        self.assertIs(raised.exception, failure)
        self.assertEqual(opened.raw.rollback.call_count, 2)
        opened.raw.commit.assert_not_called()
        opened.close.assert_called_once()

    def test_driver_operation_failure_is_safe_and_rolls_back(self):
        opened = self.prepared_connection()
        with patch.object(self.db, "_open", return_value=opened):
            with self.assertRaises(database.DatabaseError) as raised:
                with self.db.connection():
                    raise DriverError("test-only-secret SQL details", 1045)
        self.assertNotIn("test-only-secret", str(raised.exception))
        self.assertEqual(opened.raw.rollback.call_count, 2)
        opened.raw.commit.assert_not_called()
        opened.close.assert_called_once()

    def test_commit_failure_rolls_back_and_closes_connection(self):
        opened = self.prepared_connection()
        opened.raw.commit.side_effect = DriverError("test-only-secret", 2013)
        with patch.object(self.db, "_open", return_value=opened), self.assertRaises(database.DatabaseError):
            with self.db.connection():
                pass
        self.assertEqual(opened.raw.rollback.call_count, 2)
        opened.close.assert_called_once()

    def test_missing_schema_marker_rejects_operation_and_closes(self):
        opened = self.prepared_connection(marker=False)
        with patch.object(self.db, "_open", return_value=opened):
            with self.assertRaisesRegex(database.DatabaseError, "Inicializa"):
                with self.db.connection():
                    self.fail("The operation must not begin without a schema")
        opened.raw.start_transaction.assert_not_called()
        opened.raw.commit.assert_not_called()
        opened.raw.rollback.assert_called_once()
        opened.close.assert_called_once()

    def installer_connection(self, version="8.0.42", lock=1, fail_ddl=False):
        raw = Mock(autocommit=False)
        statements = []
        def execute(sql, params=()):
            statements.append((sql, params, raw.autocommit))
            if "SELECT VERSION()" in sql:
                return cursor({"version": version})
            if "GET_LOCK" in sql:
                return cursor({"adquirido": lock})
            if fail_ddl and sql.lstrip().startswith("CREATE TABLE"):
                raise DriverError("test-only-secret", 1142)
            return cursor()
        opened = SimpleNamespace(raw=raw, execute=Mock(side_effect=execute), close=Mock())
        return opened, statements

    def test_initialize_runs_explicit_ddl_in_autocommit_without_data_transaction(self):
        opened, statements = self.installer_connection()
        server = Mock()
        with patch.object(self.db, "_open", side_effect=[server, opened]) as open_db:
            self.db.initialize(create_database=True)
        self.assertEqual(open_db.call_args_list[0].kwargs, {"with_database": False})
        self.assertIn("CREATE DATABASE IF NOT EXISTS `unit_test`", server.execute.call_args.args[0])
        server.close.assert_called_once()
        ddl = [item for item in statements if item[0].lstrip().startswith("CREATE TABLE")]
        self.assertTrue(ddl)
        self.assertTrue(all(autocommit is True for _, _, autocommit in ddl))
        opened.raw.start_transaction.assert_not_called()
        self.assertTrue(any("INSERT INTO schema_migrations" in sql for sql, _, _ in statements))
        self.assertTrue(any("RELEASE_LOCK" in sql for sql, _, _ in statements))
        opened.close.assert_called_once()

    def test_unsupported_servers_are_rejected_before_ddl(self):
        for version in ("5.7.44", "8.0.15", "10.11.6-MariaDB"):
            opened, statements = self.installer_connection(version=version)
            with self.subTest(version=version), patch.object(self.db, "_open", return_value=opened):
                with self.assertRaisesRegex(database.DatabaseError, "MySQL"):
                    self.db.initialize()
            self.assertFalse(any(sql.lstrip().startswith("CREATE TABLE") for sql, _, _ in statements))
            opened.close.assert_called_once()

    def test_unavailable_installation_lock_rejects_ddl(self):
        opened, statements = self.installer_connection(lock=0)
        with patch.object(self.db, "_open", return_value=opened), self.assertRaises(database.DatabaseError):
            self.db.initialize()
        self.assertFalse(any("CREATE TABLE" in sql for sql, _, _ in statements))
        opened.close.assert_called_once()

    def test_failed_ddl_releases_lock_without_marking_schema_complete(self):
        opened, statements = self.installer_connection(fail_ddl=True)
        with patch.object(self.db, "_open", return_value=opened):
            with self.assertRaises(database.DatabaseError) as raised:
                self.db.initialize()
        self.assertNotIn("test-only-secret", str(raised.exception))
        self.assertFalse(any("INSERT INTO schema_migrations" in sql for sql, _, _ in statements))
        self.assertTrue(any("RELEASE_LOCK" in sql for sql, _, _ in statements))
        opened.close.assert_called_once()


class InitializationCLITests(unittest.TestCase):
    def test_explicit_create_flag_and_safe_failure_exit_code(self):
        spec = importlib.util.spec_from_file_location("messi_init_cli_test", ROOT / "scripts" / "init_database.py")
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        config = database.MySQLConfig(password="test-only-secret", database="cli_test")
        installer = Mock()
        with patch.object(cli.MySQLConfig, "from_environment", return_value=config), \
                patch.object(cli, "MySQLDatabase", return_value=installer), \
                patch.object(sys, "argv", ["init_database.py", "--create-database"]), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(), 0)
        installer.initialize.assert_called_once_with(create_database=True)
        stderr = io.StringIO()
        with patch.object(cli.MySQLConfig, "from_environment", side_effect=database.DatabaseError("Configura MySQL")), \
                patch.object(sys, "argv", ["init_database.py"]), contextlib.redirect_stderr(stderr):
            self.assertEqual(cli.main(), 1)
        self.assertIn("Configura MySQL", stderr.getvalue())
        self.assertNotIn("test-only-secret", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
