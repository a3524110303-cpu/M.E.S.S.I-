"""Genera dos CSV anónimos artificiales; nunca lee expedientes reales."""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "synthetic"
SEED = 2026
FEATURES = ("nota_parcial", "asistencia", "tareas_entregadas")


def _clip(value: float, upper: float) -> float:
    return round(max(0.0, min(upper, value)), 2)


def make_training_rows(count: int = 240, seed: int = SEED) -> list[dict]:
    """Simula variables correlacionadas y una etiqueta artificial ruidosa."""
    if not 20 <= count <= 10_000:
        raise ValueError("La demostración requiere entre 20 y 10,000 filas.")
    rng = random.Random(seed)
    rows = []
    for index in range(1, count + 1):
        engagement = rng.uniform(0.0, 1.0)
        grade = _clip(2.2 + 7.0 * engagement + rng.gauss(0.0, 1.35), 10.0)
        attendance = _clip(30.0 + 68.0 * engagement + rng.gauss(0.0, 15.0), 100.0)
        homework = _clip(15.0 + 84.0 * engagement + rng.gauss(0.0, 18.0), 100.0)
        simulated_final = (
            0.55 * grade + 0.20 * attendance / 10.0 + 0.25 * homework / 10.0
            + rng.gauss(0.0, 0.9)
        )
        rows.append(
            {
                "id_estudiante": f"EST-{index:04d}",
                "nota_parcial": grade,
                "asistencia": attendance,
                "tareas_entregadas": homework,
                "resultado_final": int(simulated_final < 6.0),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict], training: bool) -> None:
    fields = ["id_estudiante", *FEATURES]
    if training:
        fields.append("resultado_final")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=240)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    try:
        training_rows = make_training_rows(args.rows, args.seed)
    except ValueError as exc:
        parser.error(str(exc))
    demo_rows = [
        {"id_estudiante": f"EST-{9001 + index:04d}", **dict(zip(FEATURES, values, strict=True))}
        for index, values in enumerate(
            [(8.8, 96.0, 94.0), (4.2, 55.0, 40.0), (6.1, 80.0, 76.0),
             (3.4, 90.0, 85.0), (9.0, 52.0, 35.0), (5.6, 65.0, 50.0),
             (7.5, 87.0, 88.0), (2.9, 38.0, 22.0)]
        )
    ]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT_DIR / "training_synthetic.csv", training_rows, training=True)
    write_csv(OUTPUT_DIR / "students_demo.csv", demo_rows, training=False)
    print(f"CSV sintéticos generados: {len(training_rows)} entrenamiento, {len(demo_rows)} demostración.")
    print(f"Semilla: {args.seed}. Las etiquetas no proceden de estudiantes reales.")


if __name__ == "__main__":
    main()
