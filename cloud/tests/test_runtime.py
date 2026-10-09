from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from cloud import runtime


class CloudConfigurationTests(SimpleTestCase):
    def configuration(self, **changes):
        values = {
            "secret_key": "tests-only-secret-key-with-adequate-entropy-not-for-production-2026!",
            "db_host": "mysql.example.test", "db_name": "cloud_test",
            "db_user": "test_user", "db_password": "PRIVATE_DB_PASSWORD_82df",
            "allowed_hosts": ["messi.example.streamlit.app"],
            "csrf_trusted_origins": ["https://messi.example.streamlit.app"],
            "db_port": 3306,
            "ssl_ca_pem": "-----BEGIN CERTIFICATE-----\nTEST_CA_ONLY\n-----END CERTIFICATE-----",
        }
        values.update(changes)
        return values

    def test_production_configuration_requires_verified_mysql_tls_and_forces_no_sqlite(self):
        values = runtime.configuration_environment(self.configuration())
        self.assertEqual(values["MESSI_WEB_ENV"], "production")
        self.assertEqual(values["MESSI_WEB_TEST_SQLITE"], "0")
        self.assertEqual(values["MESSI_WEB_DB_SSL_VERIFY"], "1")
        self.assertTrue(values["MESSI_WEB_DB_SSL_CA"].endswith("cloud-mysql-ca.pem"))

    def test_missing_connection_values_fail_without_showing_existing_secrets(self):
        configuration = self.configuration(db_name="")
        with self.assertRaises(runtime.CloudConfigurationError) as error:
            runtime.configuration_environment(configuration)
        self.assertIn("db_name", str(error.exception))
        self.assertNotIn(configuration["db_password"], str(error.exception))
        self.assertNotIn(configuration["secret_key"], str(error.exception))

    def test_production_rejects_missing_or_malformed_provider_ca(self):
        for certificate in ("", "not-a-certificate", "-----BEGIN CERTIFICATE-----"):
            with self.subTest(certificate=certificate), self.assertRaises(runtime.CloudConfigurationError):
                runtime.configuration_environment(self.configuration(ssl_ca_pem=certificate))

    def test_production_rejects_short_or_development_secret(self):
        for secret in ("short", "a" * 64, "django-insecure-" + "abcdEF12!" * 8):
            with self.subTest(secret=secret), self.assertRaises(runtime.CloudConfigurationError):
                runtime.configuration_environment(self.configuration(secret_key=secret))

    def test_production_rejects_local_mysql_and_connection_urls(self):
        for host in ("localhost", "127.0.0.1", "::1", "mysql://example.test", "/tmp/mysql.sock"):
            with self.subTest(host=host), self.assertRaises(runtime.CloudConfigurationError):
                runtime.configuration_environment(self.configuration(db_host=host))

    def test_production_rejects_host_wildcards_and_http_origins(self):
        for changes in ({"allowed_hosts": ["*"]}, {"allowed_hosts": [".example.test"]},
                        {"csrf_trusted_origins": ["http://messi.example.streamlit.app"]},
                        {"csrf_trusted_origins": ["https://messi.example.streamlit.app/path"]}):
            with self.subTest(changes=changes), self.assertRaises(runtime.CloudConfigurationError):
                runtime.configuration_environment(self.configuration(**changes))

    def test_invalid_database_ports_are_rejected(self):
        for port in (0, -1, 65536, "abc", None):
            with self.subTest(port=port), self.assertRaises(runtime.CloudConfigurationError):
                runtime.configuration_environment(self.configuration(db_port=port))

    def test_local_test_opt_in_still_uses_mysql_and_explicit_http_origin(self):
        values = runtime.configuration_environment(self.configuration(
            db_host="127.0.0.1", csrf_trusted_origins=["http://127.0.0.1:8501"],
            ssl_ca_pem="",
        ), local_test=True)
        self.assertEqual(values["MESSI_WEB_ENV"], "development")
        self.assertEqual(values["MESSI_WEB_TEST_SQLITE"], "0")
        self.assertEqual(values["MESSI_WEB_DB_SSL_VERIFY"], "0")

    def test_initialize_missing_secrets_returns_safe_error_without_traceback(self):
        errors = []
        app = SimpleNamespace(secrets={}, error=errors.append)
        self.assertFalse(runtime.initialize(app))
        self.assertEqual(len(errors), 1)
        self.assertIn("[messi_web]", errors[0])

    def test_initialize_invalid_configuration_does_not_show_raw_private_values(self):
        errors = []
        configuration = self.configuration(db_name="")
        app = SimpleNamespace(secrets={"messi_web": configuration}, error=errors.append)
        self.assertFalse(runtime.initialize(app))
        self.assertNotIn(configuration["db_password"], "\n".join(errors))
        self.assertNotIn(configuration["secret_key"], "\n".join(errors))

    def test_initialization_failure_is_sanitized(self):
        errors = []
        app = SimpleNamespace(secrets={"messi_web": self.configuration()}, error=errors.append)
        with patch("cloud.runtime._CONFIG_DIGEST", None), patch(
            "cloud.runtime._compatible_settings", side_effect=RuntimeError("PRIVATE_EXCEPTION_27ea")
        ) as settings_check:
            self.assertFalse(runtime.initialize(app))
            settings_check.assert_called_once()
        self.assertNotIn("PRIVATE_EXCEPTION_27ea", "\n".join(errors))
        self.assertNotIn(self.configuration()["db_password"], "\n".join(errors))
