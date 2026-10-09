from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import salted_hmac

from portal.models import LoginAttempt


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    MESSI_LOGIN_MAX_ATTEMPTS=3,
    MESSI_LOGIN_IP_MAX_ATTEMPTS=6,
    MESSI_LOGIN_WINDOW_SECONDS=300,
    MESSI_LOGIN_BLOCK_SECONDS=300,
)
class AuthenticationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            "docente-acceso", password="Clave-correcta-2026!",
        )

    def login(self, client=None, password="incorrecta", username="docente-acceso", **headers):
        return (client or self.client).post(reverse("login"), {
            "username": username, "password": password,
        }, **headers)

    def pair_key(self, username="docente-acceso", ip="127.0.0.1"):
        return salted_hmac("messi.login.account-ip", ip + "\0" + username).hexdigest()

    def test_success_logs_in_and_clears_only_account_ip_failure_counter(self):
        self.login()
        self.login()
        response = self.login(password="Clave-correcta-2026!")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)
        self.assertEqual(LoginAttempt.objects.get(key=self.pair_key()).failures, 0)
        ip_key = salted_hmac("messi.login.ip", "127.0.0.1").hexdigest()
        self.assertEqual(LoginAttempt.objects.get(key=ip_key).failures, 2)

    def test_block_is_shared_between_sessions_and_blocks_even_correct_password(self):
        for _ in range(3):
            self.assertEqual(self.login(client=Client()).status_code, 200)
        second_device = Client()
        response = self.login(client=second_device, password="Clave-correcta-2026!")
        self.assertEqual(response.status_code, 429)
        self.assertTrue(1 <= int(response["Retry-After"]) <= 300)
        self.assertNotIn("_auth_user_id", second_device.session)
        self.assertEqual(LoginAttempt.objects.get(key=self.pair_key()).failures, 3)

    def test_expired_block_allows_successful_login(self):
        for _ in range(3):
            self.login()
        expired = timezone.now() - timedelta(seconds=301)
        LoginAttempt.objects.update(
            blocked_until=expired, window_started=expired,
        )
        response = self.login(password="Clave-correcta-2026!")
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_global_ip_limit_prevents_username_rotation(self):
        for index in range(6):
            self.assertEqual(self.login(username=f"inexistente-{index}").status_code, 200)
        response = self.login(username="otra-cuenta")
        self.assertEqual(response.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_untrusted_forwarded_headers_cannot_reset_development_limit(self):
        for index in range(3):
            self.login(HTTP_X_FORWARDED_FOR=f"192.0.2.{index}", HTTP_X_REAL_IP=f"192.0.2.{index}")
        response = self.login(HTTP_X_FORWARDED_FOR="192.0.2.200", HTTP_X_REAL_IP="192.0.2.200")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(LoginAttempt.objects.get(key=self.pair_key()).failures, 3)

    def test_throttle_records_hashes_without_passwords_or_usernames(self):
        self.login()
        keys = list(LoginAttempt.objects.values_list("key", flat=True))
        self.assertEqual(len(keys), 2)
        for key in keys:
            self.assertNotIn("docente-acceso", key)
            self.assertNotIn("incorrecta", key)
            self.assertNotIn("127.0.0.1", key)

    def test_login_requires_csrf_and_get_does_not_record_failure(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.get(reverse("login")).status_code, 200)
        self.assertEqual(LoginAttempt.objects.count(), 0)
        self.assertEqual(self.login(client=client).status_code, 403)
        self.assertEqual(LoginAttempt.objects.count(), 0)

    def test_disabled_account_does_not_authenticate(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self.login(password="Clave-correcta-2026!")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_admin_login_failed_attempts_use_same_throttle(self):
        for _ in range(3):
            response = self.client.post(reverse("admin:login"), {
                "username": "administrador-inexistente", "password": "incorrecta",
            })
            self.assertEqual(response.status_code, 200)
        response = Client().post(reverse("admin:login"), {
            "username": "administrador-inexistente", "password": "incorrecta",
        })
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)
        self.assertEqual(LoginAttempt.objects.get(key=self.pair_key("administrador-inexistente")).failures, 3)
