"""Contrato compartido de indicadores y predicciones, independiente del motor."""
import math
from messi.data import FEATURES, ID_COLUMN, ValidationError, validate_records
from messi.storage import _text

def _period(value: str) -> str:
    value = _text(value, "El periodo")
    if len(value) > 64:
        raise ValueError("El periodo debe tener como máximo 64 caracteres.")
    return value


def _support_id(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("El identificador del apoyo debe ser un entero positivo.")
    return value


def _prediction_records(records: list[dict]) -> list[dict]:
    expected = {ID_COLUMN, *FEATURES, "puntuacion_riesgo", "alerta", "origen_modelo"}
    if not isinstance(records, list) or not records:
        raise ValidationError("Ingresa al menos una predicción.")
    for record in records:
        if not isinstance(record, dict) or set(record) != expected:
            raise ValidationError("La predicción tiene campos incompletos o no permitidos.")
    indicators = validate_records([
        {key: record[key] for key in (ID_COLUMN, *FEATURES)} for record in records
    ])
    normalized = []
    for indicator, record in zip(indicators, records, strict=True):
        score = record["puntuacion_riesgo"]
        if isinstance(score, bool):
            raise ValidationError("La puntuación de riesgo debe estar entre cero y uno.")
        try:
            score = float(score)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValidationError("La puntuación de riesgo debe ser numérica.") from error
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise ValidationError("La puntuación de riesgo debe estar entre cero y uno.")
        if not isinstance(record["alerta"], bool):
            raise ValidationError("La alerta debe ser un valor booleano.")
        origin = _text(record["origen_modelo"], "El origen del modelo")
        if len(origin) > 100:
            raise ValidationError("El origen del modelo debe tener como máximo 100 caracteres.")
        normalized.append({
            **indicator, "puntuacion_riesgo": score,
            "alerta": record["alerta"], "origen_modelo": origin,
        })
    return normalized
