from pathlib import Path
from unittest.mock import patch
from unittest import skipUnless

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from messi.model import ModelUnavailable
from portal import services
from portal.models import Enrollment, FollowUp, Indicator, Prediction, SupportCase
from portal.tests.fixtures import SchoolFixture


class ConsistencyTests(SchoolFixture, TestCase):
    @skipUnless(settings.MESSI_MODEL_PATH.is_file(), "El artefacto de IA demostrativa es opcional")
    def test_existing_demo_artifact_runs_real_inference_and_persists_snapshot(self):
        prediction = services.calculate_risk(self.teacher, self.indicator.pk, self.indicator.version)
        self.assertTrue(prediction.is_current)
        self.assertGreaterEqual(prediction.score, 0)
        self.assertLessEqual(prediction.score, 1)
        self.assertEqual(len(prediction.model_version), 64)
        self.assertEqual(prediction.grade, self.indicator.grade)
        self.assertEqual(prediction.alert, prediction.score >= prediction.threshold)

    def test_stale_indicator_edit_does_not_overwrite_current_values(self):
        initial_version = self.indicator.version
        first = services.save_indicator(
            self.teacher, self.enrollment.pk, "primer_parcial", 7, 80, 90, initial_version,
        )
        with self.assertRaises(services.ConflictError):
            services.save_indicator(
                self.teacher, self.enrollment.pk, "primer_parcial", 2, 20, 30, initial_version,
            )
        self.indicator.refresh_from_db()
        self.assertEqual(self.indicator.grade, 7)
        self.assertEqual(self.indicator.version, initial_version + 1)
        self.assertEqual(first.pk, self.indicator.pk)

    def test_stale_followup_does_not_add_history_or_overwrite_status(self):
        case = services.create_case(self.tutor, self.student.pk, self.period.pk, "Acuerdo")
        initial_version = case.version
        services.add_followup(
            self.tutor, case.pk, "Primer avance", "Privado", "En seguimiento", initial_version,
        )
        with self.assertRaises(services.ConflictError):
            services.add_followup(
                self.tutor, case.pk, "Avance tardío", "", "Cerrado", initial_version,
            )
        case.refresh_from_db()
        self.assertEqual(case.status, "En seguimiento")
        self.assertEqual(case.version, initial_version + 1)
        self.assertEqual(FollowUp.objects.filter(case=case).count(), 1)

    def make_import_pair(self):
        second_enrollment = Enrollment.objects.create(student=self.other_student, group=self.group)
        second_indicator = Indicator.objects.create(
            enrollment=second_enrollment, cut="primer_parcial", grade=9,
            attendance=90, homework=90, updated_by=self.teacher,
        )
        versions = {
            str(self.enrollment.pk): self.indicator.version,
            str(second_enrollment.pk): second_indicator.version,
        }
        records = [
            {"id_estudiante": self.student.code, "nota_parcial": 7,
             "asistencia": 80, "tareas_entregadas": 85},
            {"id_estudiante": self.other_student.code, "nota_parcial": 8,
             "asistencia": 90, "tareas_entregadas": 95},
        ]
        return second_enrollment, second_indicator, records, versions

    def test_import_commits_entire_authorized_valid_batch(self):
        _, second, records, versions = self.make_import_pair()
        services.import_indicators(self.teacher, self.group.pk, "primer_parcial", records, versions)
        self.indicator.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.indicator.grade, 7)
        self.assertEqual(second.grade, 8)
        self.assertEqual(self.indicator.version, 2)
        self.assertEqual(second.version, 2)

    def test_invalid_import_last_row_rolls_back_whole_batch(self):
        _, second, records, versions = self.make_import_pair()
        records[-1]["asistencia"] = 101
        with self.assertRaises(ValidationError):
            services.import_indicators(self.teacher, self.group.pk, "primer_parcial", records, versions)
        self.indicator.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.indicator.grade, 6)
        self.assertEqual(second.grade, 9)
        self.assertEqual(self.indicator.version, 1)

    def test_stale_import_last_row_rolls_back_whole_batch(self):
        second_enrollment, second, records, versions = self.make_import_pair()
        services.save_indicator(
            self.teacher, second_enrollment.pk, "primer_parcial", 10, 100, 100, second.version,
        )
        with self.assertRaises(services.ConflictError):
            services.import_indicators(self.teacher, self.group.pk, "primer_parcial", records, versions)
        self.indicator.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.indicator.grade, 6)
        self.assertEqual(self.indicator.version, 1)
        self.assertEqual(second.grade, 10)

    def test_import_foreign_group_and_unenrolled_code_are_refused(self):
        record = [{"id_estudiante": self.other_student.code, "nota_parcial": 7,
                   "asistencia": 80, "tareas_entregadas": 85}]
        with self.assertRaises(PermissionDenied):
            services.import_indicators(
                self.teacher, self.other_group.pk, "primer_parcial", record,
                {str(self.other_enrollment.pk): self.other_indicator.version},
            )
        with self.assertRaises((PermissionDenied, ValidationError)):
            services.import_indicators(
                self.teacher, self.group.pk, "primer_parcial", record,
                {str(self.enrollment.pk): self.indicator.version},
            )
        self.assertEqual(Indicator.objects.count(), 3)

    def test_import_duplicates_do_not_write(self):
        _, second, records, versions = self.make_import_pair()
        records.append(dict(records[0]))
        with self.assertRaises(ValidationError):
            services.import_indicators(self.teacher, self.group.pk, "primer_parcial", records, versions)
        self.assertEqual(Indicator.objects.get(pk=second.pk).version, 1)

    def test_import_rejects_foreign_ids_in_snapshot(self):
        _, _, records, versions = self.make_import_pair()
        versions[str(self.other_enrollment.pk)] = self.other_indicator.version
        with self.assertRaises((PermissionDenied, ValidationError)):
            services.import_indicators(self.teacher, self.group.pk, "primer_parcial", records, versions)
        self.indicator.refresh_from_db()
        self.assertEqual(self.indicator.version, 1)

    @staticmethod
    def scored(records, *_args, **_kwargs):
        return [{**row, "puntuacion_riesgo": 0.8, "alerta": True,
                 "origen_modelo": "demo_sintetica"} for row in records]

    def fake_model(self):
        return patch("portal.services._read_metadata", return_value=(
            Path("demo.joblib"), {"threshold": 0.5, "model_sha256": "a" * 64},
        ))

    def test_risk_snapshot_becomes_stale_when_indicator_changes(self):
        with self.fake_model(), patch("portal.services.score_records", side_effect=self.scored):
            prediction = services.calculate_risk(self.teacher, self.indicator.pk, self.indicator.version)
        self.assertTrue(prediction.is_current)
        self.assertEqual(prediction.grade, self.indicator.grade)
        services.save_indicator(
            self.teacher, self.enrollment.pk, "primer_parcial", 9, 95, 95, self.indicator.version,
        )
        prediction = Prediction.objects.select_related("indicator").get(pk=prediction.pk)
        self.assertFalse(prediction.is_current)
        self.assertEqual(prediction.grade, 6)
        self.assertEqual(prediction.score, 0.8)

    def test_repeating_same_risk_version_does_not_duplicate_prediction(self):
        with self.fake_model(), patch("portal.services.score_records", side_effect=self.scored):
            first = services.calculate_risk(self.teacher, self.indicator.pk, self.indicator.version)
            second = services.calculate_risk(self.teacher, self.indicator.pk, self.indicator.version)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Prediction.objects.count(), 1)

    def test_stale_risk_request_never_creates_prediction(self):
        old_version = self.indicator.version
        services.save_indicator(
            self.teacher, self.enrollment.pk, "primer_parcial", 7, 80, 80, old_version,
        )
        with self.fake_model(), patch("portal.services.score_records", side_effect=self.scored):
            with self.assertRaises(services.ConflictError):
                services.calculate_risk(self.teacher, self.indicator.pk, old_version)
        self.assertEqual(Prediction.objects.count(), 0)

    def test_demo_model_rejects_other_academic_cut_before_inference(self):
        second_cut = services.save_indicator(
            self.teacher, self.enrollment.pk, "segundo_parcial", 7, 80, 85, 0,
        )
        with patch("portal.services.score_records") as scorer:
            with self.assertRaises(ValidationError):
                services.calculate_risk(self.teacher, second_cut.pk, second_cut.version)
            scorer.assert_not_called()
        self.assertEqual(Prediction.objects.count(), 0)

    def test_model_absence_still_allows_requests_and_support(self):
        with patch("portal.services._read_metadata", side_effect=ModelUnavailable("Modelo ausente")):
            with self.assertRaises(ModelUnavailable):
                services.calculate_risk(self.teacher, self.indicator.pk, self.indicator.version)
            request = services.create_request(self.student_user, self.period.pk, "Solicito ayuda")
            case = services.create_case(
                self.tutor, self.student.pk, self.period.pk, "Revisar tareas",
                request_id=request.pk,
            )
            services.add_followup(
                self.tutor, case.pk, "Primera sesión", "", "En seguimiento", case.version,
            )
        self.assertEqual(SupportCase.objects.count(), 1)
        self.assertEqual(FollowUp.objects.count(), 1)
        self.assertEqual(Prediction.objects.count(), 0)

    def test_indicator_change_during_inference_discards_result(self):
        def score_and_edit(records, *_args, **_kwargs):
            services.save_indicator(
                self.teacher, self.enrollment.pk, "primer_parcial", 7, 80, 90,
                self.indicator.version,
            )
            return self.scored(records)

        with self.fake_model(), patch("portal.services.score_records", side_effect=score_and_edit):
            with self.assertRaises(services.ConflictError):
                services.calculate_risk(self.teacher, self.indicator.pk, self.indicator.version)
        self.assertEqual(Prediction.objects.count(), 0)
        self.assertEqual(Indicator.objects.get(pk=self.indicator.pk).grade, 7)

    def test_model_change_during_inference_discards_result(self):
        metadata_before = {"threshold": 0.5, "model_sha256": "a" * 64}
        metadata_after = {"threshold": 0.5, "model_sha256": "b" * 64}
        with patch("portal.services._read_metadata", side_effect=[
            (Path("demo.joblib"), metadata_before), (Path("demo.joblib"), metadata_after),
        ]), patch("portal.services.score_records", side_effect=self.scored):
            with self.assertRaises(ModelUnavailable):
                services.calculate_risk(self.teacher, self.indicator.pk, self.indicator.version)
        self.assertEqual(Prediction.objects.count(), 0)

    def test_stale_alert_cannot_open_new_case(self):
        with self.fake_model(), patch("portal.services.score_records", side_effect=self.scored):
            prediction = services.calculate_risk(self.teacher, self.indicator.pk, self.indicator.version)
        services.save_indicator(
            self.teacher, self.enrollment.pk, "primer_parcial", 9, 95, 95, self.indicator.version,
        )
        with self.assertRaises(ValidationError):
            services.create_case(
                self.tutor, self.student.pk, self.period.pk, "Revisar alerta",
                prediction_id=prediction.pk,
            )
        self.assertEqual(SupportCase.objects.count(), 0)

    def test_same_request_cannot_create_duplicate_case(self):
        request = services.create_request(self.student_user, self.period.pk, "Ayuda")
        services.create_case(
            self.tutor, self.student.pk, self.period.pk, "Acuerdo",
            request_id=request.pk,
        )
        with self.assertRaises(services.ConflictError):
            services.create_case(
                self.tutor, self.student.pk, self.period.pk, "Duplicado",
                request_id=request.pk,
            )
        self.assertEqual(SupportCase.objects.count(), 1)
        request.refresh_from_db()
        self.assertEqual(request.status, "Atendida")

    def test_invalid_followup_state_creates_no_history(self):
        case = services.create_case(self.tutor, self.student.pk, self.period.pk, "Acuerdo")
        with self.assertRaises(ValidationError):
            services.add_followup(
                self.tutor, case.pk, "Avance", "", "estado_inventado", case.version,
            )
        self.assertEqual(FollowUp.objects.count(), 0)
        self.assertEqual(SupportCase.objects.get(pk=case.pk).version, 1)
