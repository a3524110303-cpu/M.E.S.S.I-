"""Arranque de producción probado sin conectar ni leer secretos reales."""
import json
import os
from pathlib import Path
import subprocess
import sys

from django.test import SimpleTestCase


class ProductionSettingsTests(SimpleTestCase):
    web_dir = Path(__file__).resolve().parents[2]

    def inspect_settings(self, changes=None, *, defaults=True):
        environment = {key: value for key, value in os.environ.items() if not key.startswith("MESSI_WEB_")}
        if defaults:
            environment.update({
                "MESSI_WEB_ENV": "production",
                "MESSI_WEB_SECRET_KEY": "test-only-secret-with-sufficient-entropy-for-settings-2026-abcXYZ!",
                "MESSI_WEB_ALLOWED_HOSTS": "messi.example.test",
                "MESSI_WEB_CSRF_TRUSTED_ORIGINS": "https://messi.example.test",
                "MESSI_WEB_DB_NAME": "messi_config_test",
                "MESSI_WEB_DB_USER": "test_user",
                "MESSI_WEB_DB_PASSWORD": "test-only-password",
                "MESSI_WEB_DB_HOST": "database",
            })
        for key, value in (changes or {}).items():
            if value is None:
                environment.pop(key, None)
            else:
                environment[key] = value
        code = (
            "import json,dotenv;dotenv.load_dotenv=lambda *a,**k:None;"
            "import config.settings as s;"
            "print(json.dumps({'engine':s.DATABASES['default']['ENGINE'],"
            "'debug':s.DEBUG,'ssl':s.SECURE_SSL_REDIRECT,"
            "'session_secure':s.SESSION_COOKIE_SECURE,'csrf_secure':s.CSRF_COOKIE_SECURE,"
            "'hsts':s.SECURE_HSTS_SECONDS,'hosts':s.ALLOWED_HOSTS}))"
        )
        return subprocess.run(
            [sys.executable, "-c", code], cwd=self.web_dir, env=environment,
            capture_output=True, text=True, timeout=20, check=False,
        )

    def assert_refused(self, changes, expected_message):
        result = self.inspect_settings(changes)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_message, result.stderr)

    def test_default_mode_is_production_and_requires_secret(self):
        result = self.inspect_settings(defaults=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MESSI_WEB_SECRET_KEY", result.stderr)

    def test_production_uses_mysql_and_enforces_https_cookie_settings(self):
        result = self.inspect_settings()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["engine"], "django.db.backends.mysql")
        self.assertFalse(data["debug"])
        self.assertTrue(data["ssl"])
        self.assertTrue(data["session_secure"])
        self.assertTrue(data["csrf_secure"])
        self.assertGreaterEqual(data["hsts"], 31536000)

    def test_production_rejects_missing_database_instead_of_sqlite_fallback(self):
        self.assert_refused({"MESSI_WEB_DB_PASSWORD": None}, "MESSI_WEB_DB_PASSWORD")
        self.assert_refused({"MESSI_WEB_DB_HOST": None}, "MESSI_WEB_DB_HOST")

    def test_production_rejects_explicit_test_sqlite(self):
        self.assert_refused({"MESSI_WEB_TEST_SQLITE": "1"}, "SQLite")

    def test_production_rejects_short_or_trivial_secret(self):
        self.assert_refused({"MESSI_WEB_SECRET_KEY": "corta"}, "MESSI_WEB_SECRET_KEY")
        self.assert_refused({"MESSI_WEB_SECRET_KEY": "a" * 64}, "MESSI_WEB_SECRET_KEY")

    def test_production_rejects_wildcard_hosts_and_http_csrf_origins(self):
        self.assert_refused({"MESSI_WEB_ALLOWED_HOSTS": "*"}, "MESSI_WEB_ALLOWED_HOSTS")
        self.assert_refused({"MESSI_WEB_CSRF_TRUSTED_ORIGINS": "http://messi.example.test"}, "HTTPS")
        self.assert_refused({"MESSI_WEB_CSRF_TRUSTED_ORIGINS": "https://messi.example.test/ruta"}, "HTTPS")

    def test_development_without_explicit_sqlite_still_requires_mysql(self):
        self.assert_refused({"MESSI_WEB_ENV": "development", "MESSI_WEB_DB_PASSWORD": None}, "MESSI_WEB_DB_PASSWORD")

    def test_test_sqlite_requires_both_development_and_explicit_opt_in(self):
        result = self.inspect_settings({
            "MESSI_WEB_ENV": "development", "MESSI_WEB_TEST_SQLITE": "1",
            "MESSI_WEB_SQLITE_PATH": ":memory:",
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["engine"], "django.db.backends.sqlite3")
