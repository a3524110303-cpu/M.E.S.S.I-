"""Permisos de equipo: cuentas administradas y cambios verificados en MySQL."""
import importlib.util
import os
from pathlib import Path
import secrets
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from messi.database import DatabaseError, MySQLConfig, MySQLDatabase
from messi.mysql_storage import MySQLStore

spec = importlib.util.spec_from_file_location("messi_permissions", ROOT / "scripts/manage_mysql_users.py")
permissions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(permissions)


class PermissionsTests(unittest.TestCase):
    def setUp(self):
        self.config = MySQLConfig(user="administrador", database="messi_test")
        self.db = Mock()
        self.db.execute.return_value.fetchone.return_value = None
        self.db.execute.return_value.fetchall.return_value = []

    def apply(self, action, **kwargs):
        with patch.object(permissions, "MySQLDatabase") as factory:
            factory.return_value._open.return_value = self.db
            return permissions.manage(self.config, action, **kwargs)

    def test_create_grants_scoped_role_without_administrator_permissions(self):
        self.apply("create", username="integrante", password="clave_de_prueba", role="editor")
        consultas = [(call.args[0], call.args[1] if len(call.args) > 1 else ())
                     for call in self.db.execute.call_args_list]
        self.assertTrue(any("SELECT, INSERT, UPDATE, DELETE ON `messi_test`.*" in sql for sql, _ in consultas))
        self.assertFalse(any("ALL PRIVILEGES" in sql or "GRANT OPTION" in sql for sql, _ in consultas))
        create = next((sql, args) for sql, args in consultas if sql.startswith("CREATE USER"))
        self.assertNotIn("clave_de_prueba", create[0])
        self.assertEqual(create[1], ("integrante", "127.0.0.1", "clave_de_prueba"))
        self.db.close.assert_called_once()

    def test_direct_grants_reject_apparent_downgrade(self):
        self.db.execute.return_value.fetchone.return_value = {"PRIVILEGE_TYPE": "INSERT"}
        with self.assertRaisesRegex(DatabaseError, "permisos directos"):
            self.apply("set-role", username="integrante", role="lector")
        self.assertFalse(any(call.args[0].startswith("GRANT ") for call in self.db.execute.call_args_list))
        self.db.close.assert_called_once()

    def test_unmanaged_role_rejects_apparent_downgrade(self):
        self.db.execute.return_value.fetchall.return_value = [{"rol": "otro_rol", "origen": "%"}]
        with self.assertRaisesRegex(DatabaseError, "otros roles"):
            self.apply("set-role", username="integrante", role="lector")
        self.assertFalse(any(call.args[0].startswith("GRANT ") for call in self.db.execute.call_args_list))

    def test_editor_role_is_removed_when_switching_to_reader(self):
        roles = permissions.role_names(self.config.database)
        def result(sql, params=()):
            cursor = Mock()
            cursor.fetchone.return_value = None
            cursor.fetchall.return_value = ([{"rol": roles["editor"], "origen": "%"}]
                                          if "mysql.role_edges" in sql else [])
            return cursor
        self.db.execute.side_effect = result
        self.apply("set-role", username="integrante", role="lector")
        self.db.execute.assert_any_call("REVOKE %s FROM %s@%s", (roles["editor"], "integrante", "127.0.0.1"))
        self.db.execute.assert_any_call("SET DEFAULT ROLE %s TO %s@%s", (roles["lector"], "integrante", "127.0.0.1"))

    def test_invalid_accounts_and_administrator_are_rejected_before_connection(self):
        with patch.object(permissions, "MySQLDatabase") as factory:
            for username in ("administrador", "bad' DROP USER", "", "x" * 33):
                with self.subTest(username=username), self.assertRaises(DatabaseError):
                    permissions.manage(self.config, "block", username)
            factory.assert_not_called()

    def test_roles_are_separate_for_each_database(self):
        self.assertNotEqual(permissions.role_names("messi_test"), permissions.role_names("messi_otro_test"))
        self.assertTrue(all(len(name) <= 32 for name in permissions.role_names("x" * 64).values()))


@unittest.skipUnless(os.environ.get("MESSI_TEST_MYSQL") == "1", "MySQL aislado no solicitado")
class RealPermissionsTests(unittest.TestCase):
    def test_editor_reader_block_and_direct_grants(self):
        config = MySQLConfig.from_environment(ROOT)
        if not config.database.endswith("_test"):
            self.skipTest("Los permisos reales sólo se prueban en una base *_test")
        database = MySQLDatabase(config)
        database.initialize(create_database=True)
        username = "perm_" + secrets.token_hex(6)
        password = secrets.token_urlsafe(24)
        student = "EST-" + str(secrets.randbelow(100000000)).zfill(8)
        user_host = os.environ.get("MESSI_TEST_MYSQL_USER_HOST", "127.0.0.1")
        permissions.manage(config, "create", username, user_host=user_host, role="editor", password=password)
        self.addCleanup(self.cleanup_account, database, username, student, user_host)
        member = MySQLConfig(host=config.host, port=config.port, user=username, password=password, database=config.database)
        store = MySQLStore(member)
        store.create_request(student, "Prueba de editor")
        permissions.manage(config, "set-role", username, user_host=user_host, role="lector")
        self.assertEqual(len(store.list_requests(student)), 1)
        with self.assertRaises(DatabaseError):
            store.create_request(student, "Lector no debe escribir")
        permissions.manage(config, "block", username, user_host=user_host)
        with self.assertRaises(DatabaseError):
            store.list_requests(student)
        permissions.manage(config, "unblock", username, user_host=user_host)
        permissions.manage(config, "set-role", username, user_host=user_host, role="editor")
        store.create_request(student, "Editor restaurado")
        raw = database._open()
        try:
            raw.raw.autocommit = True
            raw.execute(f"GRANT SELECT ON `{config.database}`.* TO %s@%s", (username, user_host))
        finally:
            raw.close()
        with self.assertRaisesRegex(DatabaseError, "permisos directos"):
            permissions.manage(config, "set-role", username, user_host=user_host, role="lector")

    @staticmethod
    def cleanup_account(database, username, student, user_host):
        raw = database._open()
        try:
            raw.raw.autocommit = True
            raw.execute("DROP USER %s@%s", (username, user_host))
            raw.execute("DELETE FROM requests WHERE student_id = %s", (student,))
            raw.execute("DELETE FROM students WHERE id = %s", (student,))
        finally:
            raw.close()
