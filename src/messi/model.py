"""Inferencia opcional con el modelo local de demostración de MESSI.

Los archivos joblib pueden ejecutar código al abrirse. Este módulo sólo acepta
artefactos del directorio models de este proyecto, creados por train_demo.py.
No admite modelos subidos desde el navegador ni descargados de terceros.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from .data import FEATURES, ID_COLUMN, MAX_ROWS, TARGET, ValidationError, _coerce_record

TRUSTED_MODEL_DIR = Path(__file__).resolve().parents[2] / "models"


class ModelUnavailable(ValueError):
    """El modelo está pendiente o su artefacto no cumple el contrato local."""


def _read_metadata(model_path: Path) -> tuple[Path, dict]:
    try:
        candidate = model_path.resolve()
        trusted_directory = TRUSTED_MODEL_DIR.resolve()
    except (AttributeError, OSError, RuntimeError) as exc:
        raise ModelUnavailable("Usa la ruta Path de un modelo local de MESSI.") from exc
    if candidate.parent != trusted_directory or candidate.suffix != ".joblib":
        raise ModelUnavailable("Sólo se permiten modelos locales del directorio models.")
    try:
        if not candidate.is_file():
            raise ModelUnavailable(
                "Modelo pendiente: ejecuta scripts/train_demo.py para crear la demostración sintética."
            )
        metadata_path = candidate.with_suffix(".json").resolve()
        if metadata_path.parent != trusted_directory:
            raise ModelUnavailable("Sólo se permiten metadatos locales del directorio models.")
        if candidate.stat().st_size > 25 * 1024 * 1024:
            raise ModelUnavailable("El artefacto local supera el tamaño admitido.")
        if metadata_path.stat().st_size > 100_000:
            raise ModelUnavailable("Los metadatos del modelo tienen un tamaño inválido.")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ModelUnavailable("Faltan metadatos válidos para el modelo local.") from exc
    if not isinstance(metadata, dict):
        raise ModelUnavailable("Los metadatos del modelo tienen un formato inválido.")
    if (
        type(metadata.get("metadata_version")) is not int
        or metadata.get("metadata_version") != 1
        or metadata.get("features") != list(FEATURES)
        or metadata.get("target") != TARGET
        or metadata.get("class_meaning") != {"0": "aprobado", "1": "reprobado"}
        or metadata.get("demo_only") is not True
        or metadata.get("training_data_source") != "synthetic"
    ):
        raise ModelUnavailable("El modelo no corresponde a la demostración sintética de MESSI.")
    threshold = metadata.get("threshold")
    if (
        not isinstance(threshold, (int, float))
        or isinstance(threshold, bool)
        or not math.isfinite(threshold)
        or not 0.0 < threshold < 1.0
    ):
        raise ModelUnavailable("El umbral de demostración del modelo es inválido.")
    try:
        digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
    except OSError as exc:
        raise ModelUnavailable("No se pudo leer el modelo local.") from exc
    if metadata.get("model_sha256") != digest:
        raise ModelUnavailable("El modelo y sus metadatos no coinciden. Regenera la demostración.")
    return candidate, metadata


def score_records(records: list[dict], model_path: Path) -> list[dict]:
    """Añade riesgo 0..1 y alerta booleana; no usa resultado_final como entrada.

    La puntuación procede exclusivamente de datos sintéticos y no representa
    una probabilidad calibrada o validada para estudiantes reales.
    """
    if not isinstance(records, list) or not records or len(records) > MAX_ROWS:
        raise ValidationError("Proporciona entre 1 y 10,000 registros válidos.")
    normalized: list[dict] = []
    seen_ids: set[str] = set()
    for row_number, record in enumerate(records, start=2):
        if not isinstance(record, dict):
            raise ValidationError(f"Fila {row_number}: registro inválido.")
        clean = _coerce_record(record, row_number, training=False)
        if clean[ID_COLUMN] in seen_ids:
            raise ValidationError(f"Fila {row_number}: identificador anónimo duplicado.")
        seen_ids.add(clean[ID_COLUMN])
        normalized.append(clean)
    candidate, metadata = _read_metadata(model_path)
    try:
        import joblib
    except ImportError as exc:
        raise ModelUnavailable(
            "Faltan dependencias de IA: instala los requisitos del proyecto para habilitar la demo."
        ) from exc
    try:
        # La comprobación de ruta y procedencia precede a la deserialización.
        pipeline = joblib.load(candidate)
        classifier = pipeline.named_steps["classifier"]
        classes = list(classifier.classes_)
        if classes != [0, 1]:
            raise ModelUnavailable("El modelo no contiene las clases 0 y 1 esperadas.")
        matrix = [[record[feature] for feature in FEATURES] for record in normalized]
        probabilities = pipeline.predict_proba(matrix)
        if len(probabilities) != len(normalized):
            raise ModelUnavailable("El modelo devolvió una cantidad incorrecta de resultados.")
        scored: list[dict] = []
        for record, probabilities_row in zip(normalized, probabilities, strict=True):
            if len(probabilities_row) != 2:
                raise ModelUnavailable("El modelo devolvió resultados de formato inválido.")
            risk = float(probabilities_row[classes.index(1)])
            if not math.isfinite(risk) or not 0.0 <= risk <= 1.0:
                raise ModelUnavailable("El modelo devolvió una puntuación inválida.")
            scored.append(
                {
                    **record,
                    "puntuacion_riesgo": risk,
                    "alerta": risk >= metadata["threshold"],
                    "origen_modelo": "demo_sintetica",
                }
            )
        return scored
    except ModelUnavailable:
        raise
    except (ImportError, ModuleNotFoundError) as exc:
        raise ModelUnavailable("Faltan dependencias compatibles para abrir el modelo local.") from exc
    except Exception as exc:
        raise ModelUnavailable("No se pudo utilizar el modelo local. Regenera la demostración.") from exc
