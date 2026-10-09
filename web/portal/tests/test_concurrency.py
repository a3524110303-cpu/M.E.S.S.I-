"""Carreras reales: requieren un motor con bloqueo SELECT FOR UPDATE."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connections
from django.test import Client, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.urls import reverse
from django.utils.crypto import salted_hmac

from portal import services
from portal.models import FollowUp, Indicator, LoginAttempt, Prediction, SupportCase
from portal.tests.fixtures import SchoolFixture


@skipUnlessDBFeature("has_select_for_update")
@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class SharedDatabaseConcurrencyTests(SchoolFixture, TransactionTestCase):
    def setUp(self):
        type(self).setUpTestData()

    def race(self, actions):
        barrier = Barrier(len(actions))

        def worker(action):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return action()
            except services.ConflictError:
                return "conflict"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            futures = [pool.submit(worker, action) for action in actions]
            return [future.result(timeout=30) for future in futures]

    def save_from_thread(self, grade, cut="primer_parcial", version=1):
        user = get_user_model().objects.get(pk=self.teacher.pk)
        services.save_indicator(user, self.enrollment.pk, cut, grade, 80, 85, version)
        return "saved"

    def test_parallel_edits_one_succeeds_one_reports_conflict(self):
        outcomes = self.race([
            lambda: self.save_from_thread(7), lambda: self.save_from_thread(8),
        ])
        self.assertCountEqual(outcomes, ["saved", "conflict"])
        self.indicator.refresh_from_db()
        self.assertIn(self.indicator.grade, (7, 8))
        self.assertEqual(self.indicator.version, 2)

    def test_parallel_first_creation_is_serialized_by_enrollment_lock(self):
        outcomes = self.race([
            lambda: self.save_from_thread(7, cut="segundo_parcial", version=0),
            lambda: self.save_from_thread(8, cut="segundo_parcial", version=0),
        ])
        self.assertCountEqual(outcomes, ["saved", "conflict"])
        self.assertEqual(Indicator.objects.filter(
            enrollment=self.enrollment, cut="segundo_parcial",
        ).count(), 1)

    def test_parallel_followups_do_not_silently_overwrite_case(self):
        case = services.create_case(self.tutor, self.student.pk, self.period.pk, "Acuerdo")

        def followup(status):
            user = get_user_model().objects.get(pk=self.tutor.pk)
            services.add_followup(user, case.pk, "Avance", "", status, 1)
            return "saved"

        outcomes = self.race([
            lambda: followup("En seguimiento"), lambda: followup("Cerrado"),
        ])
        self.assertCountEqual(outcomes, ["saved", "conflict"])
        self.assertEqual(FollowUp.objects.filter(case=case).count(), 1)
        self.assertEqual(SupportCase.objects.get(pk=case.pk).version, 2)

    def test_alert_case_waits_for_indicator_edit_in_same_lock_order(self):
        prediction = Prediction.objects.create(
            indicator=self.indicator, indicator_version=self.indicator.version,
            grade=self.indicator.grade, attendance=self.indicator.attendance,
            homework=self.indicator.homework, score=0.8, threshold=0.5,
            model_version="a" * 64, alert=True,
        )
        teacher_locked = Event()
        tutor_attempted_lock = Event()
        original_lock = services._locked_enrollment

        def observe_lock(user, enrollment_id):
            if user.pk == self.teacher.pk:
                enrollment = original_lock(user, enrollment_id)
                teacher_locked.set()
                if not tutor_attempted_lock.wait(timeout=10):
                    raise TimeoutError("El caso no alcanzó el bloqueo de inscripción antes del indicador")
                return enrollment
            if user.pk == self.tutor.pk:
                if not teacher_locked.wait(timeout=10):
                    raise TimeoutError("El docente no obtuvo el bloqueo de inscripción")
                tutor_attempted_lock.set()
            return original_lock(user, enrollment_id)

        def open_alert_case():
            user = get_user_model().objects.get(pk=self.tutor.pk)
            if not teacher_locked.wait(timeout=10):
                raise TimeoutError("El docente no inició la edición")
            try:
                services.create_case(
                    user, self.student.pk, self.period.pk, "Atender alerta",
                    prediction_id=prediction.pk,
                )
            except ValidationError:
                return "stale_alert"
            return "case_created"

        with patch("portal.services._locked_enrollment", side_effect=observe_lock):
            outcomes = self.race([lambda: self.save_from_thread(9), open_alert_case])
        self.assertCountEqual(outcomes, ["saved", "stale_alert"])
        self.assertEqual(Indicator.objects.get(pk=self.indicator.pk).version, 2)
        self.assertEqual(SupportCase.objects.count(), 0)

    @override_settings(MESSI_LOGIN_MAX_ATTEMPTS=3, MESSI_LOGIN_IP_MAX_ATTEMPTS=6)
    def test_parallel_login_failures_share_one_transactional_counter(self):
        username = self.teacher.username
        pair_key = salted_hmac("messi.login.account-ip", "127.0.0.1\0" + username).hexdigest()
        ip_key = salted_hmac("messi.login.ip", "127.0.0.1").hexdigest()
        LoginAttempt.objects.create(key=pair_key, failures=2)
        LoginAttempt.objects.create(key=ip_key, failures=2)

        def bad_login():
            return Client().post(reverse("login"), {
                "username": username, "password": "incorrecta",
            }).status_code

        outcomes = self.race([bad_login, bad_login])
        self.assertCountEqual(outcomes, [200, 429])
        self.assertEqual(LoginAttempt.objects.get(key=pair_key).failures, 3)
