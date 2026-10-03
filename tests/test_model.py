"""Pruebas de acceso, procedencia y aislamiento de la etiqueta de entrenamiento."""

import hashlib
import importlib.util
import json
import math
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from messi.data import FEATURES, TARGET, ValidationError
from messi.model import ModelUnavailable, score_records


RECORDS = [dict(id_estudiante="EST-001", nota_parcial=6.0, asistencia=80.0, tareas_entregadas=70.0)]


def write_fixture(directory: Path, content: bytes = b"fixture-not-a-pickle") -> Path:
    path = directory / "messi_demo.joblib"
    path.write_bytes(content)
    metadata = {
        "metadata_version": 1, "features": list(FEATURES), "target": TARGET,
        "class_meaning": {"0": "aprobado", "1": "reprobado"},
        "demo_only": True, "training_data_source": "synthetic", "threshold": 0.5,
        "model_sha256": hashlib.sha256(content).hexdigest(),
    }
    path.with_suffix(".json").write_text(json.dumps(metadata), encoding="utf-8")
    return path


class ModelContractTests(unittest.TestCase):
    def test_missing_model_has_actionable_pending_message(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            trusted = Path(directory)
            with patch("messi.model.TRUSTED_MODEL_DIR", trusted):
                with self.assertRaisesRegex(ModelUnavailable, "Modelo pendiente"):
                    score_records(RECORDS, trusted / "messi_demo.joblib")

    def test_external_model_is_rejected_before_deserialization(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            outside = Path(directory) / "outside.joblib"
            fake_loader = Mock()
            with patch.dict(sys.modules, {"joblib": types.SimpleNamespace(load=fake_loader)}):
                with self.assertRaisesRegex(ModelUnavailable, "locales"):
                    score_records(RECORDS, outside)
            fake_loader.assert_not_called()

    def test_integrity_and_metadata_are_checked_before_deserialization(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            trusted = Path(directory)
            path = write_fixture(trusted)
            path.write_bytes(b"modified")
            fake_loader = Mock()
            with patch("messi.model.TRUSTED_MODEL_DIR", trusted):
                with patch.dict(sys.modules, {"joblib": types.SimpleNamespace(load=fake_loader)}):
                    with self.assertRaisesRegex(ModelUnavailable, "no coinciden"):
                        score_records(RECORDS, path)
            fake_loader.assert_not_called()

    def test_non_demo_metadata_and_target_leakage_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            trusted = Path(directory)
            path = write_fixture(trusted)
            metadata = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
            metadata["training_data_source"] = "real"
            path.with_suffix(".json").write_text(json.dumps(metadata), encoding="utf-8")
            with patch("messi.model.TRUSTED_MODEL_DIR", trusted):
                with self.assertRaises(ModelUnavailable):
                    score_records(RECORDS, path)
                with self.assertRaises(ValidationError):
                    score_records([{**RECORDS[0], TARGET: 1}], path)

    def test_missing_optional_dependency_returns_actionable_error(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            trusted = Path(directory)
            path = write_fixture(trusted)
            with patch("messi.model.TRUSTED_MODEL_DIR", trusted):
                with patch.dict(sys.modules, {"joblib": None}):
                    with self.assertRaisesRegex(ModelUnavailable, "dependencias"):
                        score_records(RECORDS, path)

    def test_only_features_reach_model_and_original_records_are_unchanged(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            trusted = Path(directory)
            path = write_fixture(trusted)
            predict = Mock(return_value=[[0.25, 0.75]])
            pipeline = types.SimpleNamespace(
                named_steps={"classifier": types.SimpleNamespace(classes_=[0, 1])},
                predict_proba=predict,
            )
            with patch("messi.model.TRUSTED_MODEL_DIR", trusted):
                with patch.dict(sys.modules, {"joblib": types.SimpleNamespace(load=lambda _: pipeline)}):
                    results = score_records(RECORDS, path)
            predict.assert_called_once_with([[6.0, 80.0, 70.0]])
            self.assertEqual(results[0]["puntuacion_riesgo"], 0.75)
            self.assertIs(results[0]["alerta"], True)
            self.assertEqual(results[0]["origen_modelo"], "demo_sintetica")
            self.assertNotIn("puntuacion_riesgo", RECORDS[0])

    def test_invalid_probability_and_reversed_classes_fail_closed(self):
        for classes, probabilities in (([1, 0], [[0.2, 0.8]]), ([0, 1], [[0.2, float("nan")]]),
                                       ([0, 1], [[0.2, 1.2]]), ([0, 1], [])):
            with self.subTest(classes=classes, probabilities=probabilities):
                with tempfile.TemporaryDirectory(dir=ROOT) as directory:
                    trusted = Path(directory)
                    path = write_fixture(trusted)
                    pipeline = types.SimpleNamespace(
                        named_steps={"classifier": types.SimpleNamespace(classes_=classes)},
                        predict_proba=lambda _: probabilities,
                    )
                    with patch("messi.model.TRUSTED_MODEL_DIR", trusted):
                        with patch.dict(sys.modules, {"joblib": types.SimpleNamespace(load=lambda _: pipeline)}):
                            with self.assertRaises(ModelUnavailable):
                                score_records(RECORDS, path)


_ML_AVAILABLE = all(importlib.util.find_spec(name) is not None for name in ("joblib", "numpy", "sklearn"))


@unittest.skipUnless(_ML_AVAILABLE, "Prueba MLP omitida: instala las dependencias de IA del proyecto.")
class RealPipelineTests(unittest.TestCase):
    def test_local_pipeline_roundtrip(self):
        import joblib
        from sklearn.neural_network import MLPClassifier
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        # Datos pequeños artificiales para comprobar serialización e inferencia,
        # sin convertir esta prueba de software en una prueba de exactitud educativa.
        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", MLPClassifier(hidden_layer_sizes=(8,), solver="lbfgs", max_iter=500, random_state=2026)),
        ])
        pipeline.fit([[2, 20, 15], [3, 30, 25], [8, 90, 85], [9, 95, 95]], [1, 1, 0, 0])
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            trusted = Path(directory)
            path = trusted / "messi_demo.joblib"
            joblib.dump(pipeline, path)
            serialized = path.read_bytes()
            write_fixture(trusted, serialized)
            with patch("messi.model.TRUSTED_MODEL_DIR", trusted):
                scored = score_records(RECORDS, path)
        self.assertEqual(len(scored), 1)
        self.assertTrue(math.isfinite(scored[0]["puntuacion_riesgo"]))
        self.assertGreaterEqual(scored[0]["puntuacion_riesgo"], 0.0)
        self.assertLessEqual(scored[0]["puntuacion_riesgo"], 1.0)


if __name__ == "__main__":
    unittest.main()
