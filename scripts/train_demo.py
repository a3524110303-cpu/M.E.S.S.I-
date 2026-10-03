"""Entrena una demostración sintética de MESSI con train/validación/prueba separados."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from messi.data import FEATURES, TARGET, ValidationError, load_csv  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    try:
        import joblib
        import numpy as np
        import sklearn
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import (
            accuracy_score, balanced_accuracy_score, confusion_matrix,
            f1_score, precision_score, recall_score, roc_auc_score,
        )
        from sklearn.model_selection import train_test_split
        from sklearn.neural_network import MLPClassifier
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        print("Faltan dependencias de IA. Instala requirements.txt antes de entrenar.", file=sys.stderr)
        return 2

    source_path = PROJECT_ROOT / "data" / "synthetic" / "training_synthetic.csv"
    try:
        records = load_csv(source_path, training=True)
    except ValidationError as exc:
        print(f"Datos de demostración inválidos: {exc}", file=sys.stderr)
        return 2
    features = np.asarray([[row[name] for name in FEATURES] for row in records], dtype=float)
    target = np.asarray([row[TARGET] for row in records], dtype=int)
    classes, counts = np.unique(target, return_counts=True)
    if list(classes) != [0, 1] or min(counts) < 10:
        print("La demo necesita ambas clases y al menos 10 filas por clase.", file=sys.stderr)
        return 2

    # La prueba se reserva antes del ajuste; el escalador aprende sólo con entrenamiento.
    train_validation_x, test_x, train_validation_y, test_y = train_test_split(
        features, target, test_size=0.20, stratify=target, random_state=args.seed,
    )
    train_x, validation_x, train_y, validation_y = train_test_split(
        train_validation_x, train_validation_y, test_size=0.25,
        stratify=train_validation_y, random_state=args.seed,
    )
    logistic = Pipeline(
        [("scaler", StandardScaler()),
         ("classifier", LogisticRegression(max_iter=1000, random_state=args.seed))]
    )
    mlp = Pipeline(
        [("scaler", StandardScaler()),
         ("classifier", MLPClassifier(
             hidden_layer_sizes=(8,), max_iter=1000, early_stopping=True,
             validation_fraction=0.15, n_iter_no_change=30, random_state=args.seed,
         ))]
    )
    logistic.fit(train_x, train_y)
    mlp.fit(train_x, train_y)

    def metrics_for(x, y, pipeline=None) -> dict:
        if pipeline is None:
            predicted = (x[:, 0] < 6.0).astype(int)
            risk = 1.0 - x[:, 0] / 10.0
        else:
            positive_index = list(pipeline.named_steps["classifier"].classes_).index(1)
            risk = pipeline.predict_proba(x)[:, positive_index]
            predicted = (risk >= 0.5).astype(int)
        return {
            "accuracy": float(accuracy_score(y, predicted)),
            "balanced_accuracy": float(balanced_accuracy_score(y, predicted)),
            "precision_risk": float(precision_score(y, predicted, zero_division=0)),
            "recall_risk": float(recall_score(y, predicted, zero_division=0)),
            "f1_risk": float(f1_score(y, predicted, zero_division=0)),
            "roc_auc": float(roc_auc_score(y, risk)),
            "confusion_matrix_labels_0_1": confusion_matrix(y, predicted, labels=[0, 1]).tolist(),
        }

    candidates = {"regla_nota_menor_6": None, "regresion_logistica": logistic, "mlp_8": mlp}
    evaluations = {
        split_name: {name: metrics_for(x, y, estimator) for name, estimator in candidates.items()}
        for split_name, x, y in (
            ("validation", validation_x, validation_y), ("test_holdout", test_x, test_y)
        )
    }
    models_dir = PROJECT_ROOT / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / "messi_demo.joblib"
    joblib.dump(mlp, model_path)
    metadata = {
        "metadata_version": 1,
        "demo_only": True,
        "training_data_source": "synthetic",
        "source_file": "data/synthetic/training_synthetic.csv",
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "generator": "scripts/generate_synthetic.py (seed por defecto 2026)",
        "seed": args.seed,
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "sklearn_version": sklearn.__version__,
        "features": list(FEATURES),
        "target": TARGET,
        "class_meaning": {"0": "aprobado", "1": "reprobado"},
        "threshold": 0.5,
        "threshold_status": "Fijo para demo; no calibrado ni validado con datos reales.",
        "architecture": "StandardScaler + MLPClassifier hidden_layer_sizes=(8,)",
        "split_counts": {
            "training": len(train_y), "validation": len(validation_y), "test_holdout": len(test_y)
        },
        "class_counts": {str(int(label)): int(count) for label, count in zip(classes, counts, strict=True)},
        "evaluations": evaluations,
        "limitations": (
            "Etiquetas artificiales. Métricas de software sobre simulación; no demuestran eficacia "
            "educativa, equidad o probabilidad calibrada. La alerta requiere revisión humana. "
            "El MLP se conserva por alcance didáctico; la tabla no selecciona un ganador."
        ),
    }
    model_path.with_suffix(".json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8"
    )
    print("DEMO SINTÉTICA: métricas sin validación con estudiantes reales.")
    print(f"Separación: {len(train_y)} entrenamiento / {len(validation_y)} validación / {len(test_y)} prueba.")
    print("Umbral IA: 0.5 fijo de demostración. Regla comparativa: nota_parcial < 6.")
    print("Método                    Exactitud   Recall riesgo   F1 riesgo   ROC AUC (prueba)")
    for method, result in evaluations["test_holdout"].items():
        print(
            f"{method:25s} {result['accuracy']:8.3f} {result['recall_risk']:15.3f} "
            f"{result['f1_risk']:11.3f} {result['roc_auc']:17.3f}"
        )
    print("Modelo y reporte completo: models/messi_demo.joblib y models/messi_demo.json")
    print("Estos artefactos son locales. No añadas modelos joblib al repositorio.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
