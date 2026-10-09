from datetime import timedelta
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from cloud import auth
from portal.models import LoginAttempt, Profile
from portal.tests.fixtures import SchoolFixture


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class CloudAuthenticationTests(SchoolFixture, TestCase):
    def session(self, user=None):
        user = user or self.teacher
        return SimpleNamespace(session_state={
            "_messi_auth_user_id": user.pk,
            "_messi_auth_hash": user.get_session_auth_hash(),
            "_messi_auth_started": timezone.now().timestamp(),
            "_messi_auth_role": user.profile.role,
            "cached_private_note": "PRIVADO_SESION_f594",
        })

    def test_django_password_authenticates_existing_active_profile(self):
        user, retry = auth.authenticate_credentials(
            self.teacher.username, "Clave-de-prueba-2026!",
        )
        self.assertEqual(user.pk, self.teacher.pk)
        self.assertEqual(retry, 0)
        self.assertNotEqual(user.password, "Clave-de-prueba-2026!")

    def test_wrong_password_and_unknown_account_do_not_authenticate(self):
        for username in (self.teacher.username, "cuenta-inexistente"):
            with self.subTest(username=username):
                user, retry = auth.authenticate_credentials(username, "incorrecta")
                self.assertIsNone(user)
                self.assertEqual(retry, 0)

    def test_shared_account_counter_blocks_correct_password_after_limit(self):
        for _ in range(5):
            user, _ = auth.authenticate_credentials(self.teacher.username, "incorrecta")
            self.assertIsNone(user)
        user, retry = auth.authenticate_credentials(
            self.teacher.username, "Clave-de-prueba-2026!",
        )
        self.assertIsNone(user)
        self.assertTrue(1 <= retry <= 300)
        self.assertEqual(LoginAttempt.objects.count(), 1)
        self.assertEqual(LoginAttempt.objects.get().failures, 5)

    def test_normalized_username_cannot_bypass_shared_counter(self):
        variants = [self.teacher.username, self.teacher.username.upper(),
                    " " + self.teacher.username + " ", self.teacher.username.upper()]
        for username in variants:
            auth.authenticate_credentials(username, "incorrecta")
        auth.authenticate_credentials(self.teacher.username, "incorrecta")
        user, retry = auth.authenticate_credentials(self.teacher.username.upper(), "incorrecta")
        self.assertIsNone(user)
        self.assertGreater(retry, 0)
        self.assertEqual(LoginAttempt.objects.count(), 1)

    def test_expired_account_block_allows_correct_credentials(self):
        for _ in range(5):
            auth.authenticate_credentials(self.teacher.username, "incorrecta")
        expired = timezone.now() - timedelta(seconds=301)
        LoginAttempt.objects.update(blocked_until=expired, window_started=expired)
        user, retry = auth.authenticate_credentials(
            self.teacher.username, "Clave-de-prueba-2026!",
        )
        self.assertEqual(user.pk, self.teacher.pk)
        self.assertEqual(retry, 0)

    def test_disabled_or_unprofiled_account_does_not_authenticate(self):
        self.teacher.is_active = False
        self.teacher.save(update_fields=["is_active"])
        user, _ = auth.authenticate_credentials(self.teacher.username, "Clave-de-prueba-2026!")
        self.assertIsNone(user)
        unprofiled = get_user_model().objects.create_user(
            "sin-perfil-cloud", password="Clave-de-prueba-2026!",
        )
        user, _ = auth.authenticate_credentials(unprofiled.username, "Clave-de-prueba-2026!")
        self.assertIsNone(user)

    def test_session_fetches_current_user_without_caching_other_sessions(self):
        teacher_session = self.session(self.teacher)
        student_session = self.session(self.student_user)
        self.assertEqual(auth.get_session_user(teacher_session).pk, self.teacher.pk)
        self.assertEqual(auth.get_session_user(student_session).pk, self.student_user.pk)
        self.assertNotEqual(
            auth.get_session_user(teacher_session).pk, auth.get_session_user(student_session).pk,
        )

    def test_logout_clears_all_session_data_including_cached_private_fields(self):
        state = self.session()
        auth.logout(state)
        self.assertEqual(state.session_state, {})
        self.assertIsNone(auth.get_session_user(state))

    def test_expired_session_clears_identity_and_private_data(self):
        state = self.session()
        state.session_state["_messi_auth_started"] = (timezone.now() - timedelta(hours=8, seconds=1)).timestamp()
        self.assertIsNone(auth.get_session_user(state))
        self.assertEqual(state.session_state, {})

    def test_password_change_invalidates_existing_streamlit_session(self):
        state = self.session()
        self.teacher.set_password("Nueva-clave-2026-qa!")
        self.teacher.save(update_fields=["password"])
        self.assertIsNone(auth.get_session_user(state))
        self.assertEqual(state.session_state, {})

    def test_deactivation_invalidates_existing_streamlit_session(self):
        state = self.session()
        self.teacher.is_active = False
        self.teacher.save(update_fields=["is_active"])
        self.assertIsNone(auth.get_session_user(state))
        self.assertEqual(state.session_state, {})

    def test_role_change_invalidates_existing_streamlit_session(self):
        state = self.session()
        Profile.objects.filter(user=self.teacher).update(role="tutor")
        self.assertIsNone(auth.get_session_user(state))
        self.assertEqual(state.session_state, {})

    def test_mismatched_user_id_and_auth_hash_is_rejected(self):
        state = self.session()
        state.session_state["_messi_auth_user_id"] = self.student_user.pk
        self.assertIsNone(auth.get_session_user(state))
        self.assertEqual(state.session_state, {})

    def test_counter_stores_only_hashed_account_identifier(self):
        auth.authenticate_credentials(self.teacher.username, "incorrecta")
        key = LoginAttempt.objects.get().key
        self.assertNotIn(self.teacher.username, key)
        self.assertNotIn("incorrecta", key)
        self.assertGreater(len(key), 30)
