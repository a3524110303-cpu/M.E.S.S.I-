"""Pruebas del contrato de CSV; ejecutables sin dependencias de IA."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from messi.data import (
    FEATURES, FRIENDLY_HEADERS, ValidationError, load_csv, load_pasted,
    record_from_counts, validate_records,
)


HEADER = "id_estudiante,nota_parcial,asistencia,tareas_entregadas\n"


class DataContractTests(unittest.TestCase):
    def test_bytes_content_and_file_normalize_to_same_records(self):
        contents = HEADER + "EST-001,6.5,80,70\n"
        expected = [dict(id_estudiante="EST-001", nota_parcial=6.5, asistencia=80.0, tareas_entregadas=70.0)]
        self.assertEqual(load_csv(contents), expected)
        self.assertEqual(load_csv(b"\xef\xbb\xbf" + contents.encode()), expected)
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "students.csv"
            path.write_text(contents, encoding="utf-8")
            self.assertEqual(load_csv(path), expected)

    def test_training_target_is_separate_and_binary(self):
        contents = HEADER.rstrip() + ",resultado_final\nEST-001,6,80,70,1\n"
        self.assertEqual(load_csv(contents, training=True)[0]["resultado_final"], 1)
        with self.assertRaises(ValidationError):
            load_csv(contents)
        with self.assertRaises(ValidationError):
            load_csv(HEADER + "EST-001,6,80,70\n", training=True)
        with self.assertRaises(ValidationError):
            load_csv(contents.replace(",1\n", ",2\n"), training=True)

    def test_sensitive_extra_missing_and_duplicate_headers_are_rejected(self):
        invalid = (
            HEADER.rstrip() + ",nombre\nEST-001,6,80,70,Ana\n",
            "id_estudiante,nota_parcial,asistencia\nEST-001,6,80\n",
            "id_estudiante,nota_parcial,asistencia,asistencia\nEST-001,6,80,70\n",
        )
        for contents in invalid:
            with self.subTest(contents=contents), self.assertRaises(ValidationError):
                load_csv(contents)

    def test_invalid_values_and_ranges_are_rejected(self):
        invalid_rows = (
            "EST-001,,80,70", "EST-001,abc,80,70", "EST-001,nan,80,70",
            "EST-001,Infinity,80,70", "EST-001,-1,80,70", "EST-001,10.01,80,70",
            "EST-001,6,100.1,70", "EST-001,6,-0.1,70", "EST-001,6,80,101",
            "EST-001,6,80,-1", "EST-001,1e999,80,70", "EST-001,6,80,",
        )
        for row in invalid_rows:
            with self.subTest(row=row), self.assertRaises(ValidationError):
                load_csv(HEADER + row + "\n")

    def test_boundaries_and_column_order_are_supported(self):
        contents = "tareas_entregadas,asistencia,nota_parcial,id_estudiante\n0,100,10,EST-0001\n"
        record = load_csv(contents)[0]
        self.assertEqual([record[name] for name in FEATURES], [10.0, 100.0, 0.0])

    def test_ids_and_duplicates_are_rejected(self):
        for student_id in ("Ana", "EST-12", "EST-123456789", "EST-１２３", "EST-001@correo.mx", ""):
            with self.subTest(student_id=student_id), self.assertRaises(ValidationError):
                load_csv(HEADER + f"{student_id},6,80,70\n")
        with self.assertRaisesRegex(ValidationError, "duplicado"):
            load_csv(HEADER + "EST-001,6,80,70\nEST-001,7,90,90\n")

    def test_empty_malformed_and_bad_encoding_are_rejected(self):
        invalid = ("", HEADER, HEADER + "EST-001,6,80\n", HEADER + "EST-001,6,80,70,otro\n",
                   HEADER + 'EST-001,"6,80,70\n', b"\xff\xfe")
        for source in invalid:
            with self.subTest(source=source), self.assertRaises(ValidationError):
                load_csv(source)

    def test_byte_and_row_limits_are_enforced(self):
        with patch("messi.data.MAX_BYTES", 10), self.assertRaises(ValidationError):
            load_csv(HEADER + "EST-001,6,80,70\n")
        with patch("messi.data.MAX_ROWS", 1), self.assertRaises(ValidationError):
            load_csv(HEADER + "EST-001,6,80,70\nEST-002,7,90,90\n")

    def test_plain_string_is_content_and_missing_path_is_handled(self):
        with self.assertRaises(ValidationError):
            load_csv("students.csv")
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            with self.assertRaisesRegex(ValidationError, "leer"):
                load_csv(Path(directory) / "missing.csv")

    def test_committed_synthetic_datasets_meet_contract(self):
        synthetic_dir = Path(__file__).resolve().parents[1] / "data" / "synthetic"
        self.assertEqual(len(load_csv(synthetic_dir / "students_demo.csv")), 8)
        training = load_csv(synthetic_dir / "training_synthetic.csv", training=True)
        self.assertEqual(len(training), 240)
        self.assertEqual({row["resultado_final"] for row in training}, {0, 1})


class ManualAndPastedTests(unittest.TestCase):
    def test_counts_convert_exactly_to_percentage_contract(self):
        record = record_from_counts("EST-001", 6.5, 8, 10, 2, 3)
        self.assertEqual(record["asistencia"], 80.0)
        self.assertEqual(record["tareas_entregadas"], 200 / 3)
        self.assertEqual(record, validate_records([record])[0])
        zero = record_from_counts("EST-002", 0, 0, 10, 0, 5)
        self.assertEqual([zero[name] for name in FEATURES], [0.0, 0.0, 0.0])

    def test_invalid_counts_note_and_id_are_rejected(self):
        valid_args = dict(student_id="EST-001", nota_parcial=6.5, asistencias=8, sesiones=10,
                          tareas_entregadas=2, tareas_solicitadas=3)
        invalid_changes = (
            {"sesiones": 0}, {"tareas_solicitadas": 0}, {"sesiones": -1},
            {"asistencias": 11}, {"asistencias": -1}, {"tareas_entregadas": 4},
            {"tareas_entregadas": -1}, {"asistencias": True}, {"sesiones": 10.0},
            {"tareas_entregadas": None}, {"tareas_solicitadas": "3"},
            {"nota_parcial": 10.1}, {"nota_parcial": None}, {"student_id": "Ana"},
        )
        for changed in invalid_changes:
            with self.subTest(changed=changed), self.assertRaises(ValidationError):
                record_from_counts(**{**valid_args, **changed})

    def test_manual_records_use_same_ranges_and_reject_extra_columns(self):
        record = dict(id_estudiante="EST-001", nota_parcial="6.5", asistencia=80, tareas_entregadas=70)
        self.assertEqual(validate_records([record])[0]["nota_parcial"], 6.5)
        for modified in ({**record, "nota_parcial": 11}, {**record, "resultado_final": 1},
                         {**record, "nombre": "Ana"}, {**record, "asistencia": True}):
            with self.subTest(modified=modified), self.assertRaises(ValidationError):
                validate_records([modified])
        self.assertEqual(record["nota_parcial"], "6.5")

    def test_manual_empty_and_duplicate_ids_are_rejected(self):
        with self.assertRaises(ValidationError):
            validate_records([])
        with self.assertRaises(ValidationError):
            validate_records([dict(id_estudiante="", nota_parcial=6, asistencia=80, tareas_entregadas=70)])
        record = dict(id_estudiante="EST-001", nota_parcial=6, asistencia=80, tareas_entregadas=70)
        with self.assertRaisesRegex(ValidationError, "duplicado"):
            validate_records([record, record])

    def test_three_columns_without_headers_generate_ids_and_accept_decimal_comma(self):
        rows = load_pasted("6,5\t80\t70\n8.5\t90\t95\n")
        self.assertEqual([row["id_estudiante"] for row in rows], ["EST-0001", "EST-0002"])
        self.assertEqual(rows[0]["nota_parcial"], 6.5)

    def test_semicolon_four_columns_and_blank_ids_avoid_later_collisions(self):
        rows = load_pasted(";6,5;80;70\nEST-0001;8;90;95\n;4;60;50\n")
        self.assertEqual([row["id_estudiante"] for row in rows], ["EST-0002", "EST-0001", "EST-0003"])

    def test_friendly_and_canonical_headers_allow_column_reordering(self):
        friendly = ";".join(FRIENDLY_HEADERS) + "\n;6,5;80;70\n"
        self.assertEqual(load_pasted(friendly)[0]["nota_parcial"], 6.5)
        canonical = "asistencia\ttareas_entregadas\tid_estudiante\tnota_parcial\n80\t70\tEST-001\t6\n"
        self.assertEqual(load_pasted(canonical)[0]["nota_parcial"], 6.0)

    def test_ambiguous_delimiters_bad_headers_and_invalid_rows_are_rejected(self):
        invalid = ("6,80,70", "6\t80;70", "6;80;70\n7;90\n", "6;80;70;extra;nombre",
                   ";".join(FRIENDLY_HEADERS) + ";nombre\n;6;80;70;Ana\n",
                   "nota_parcial;asistencia;tareas_entregadas\n6;80;70\n",
                   "=SUMA(A1);80;70", "6;NaN;70", "6;101;70", "6;80%;70",
                   "", ";".join(FRIENDLY_HEADERS) + "\n")
        for contents in invalid:
            with self.subTest(contents=contents), self.assertRaises(ValidationError):
                load_pasted(contents)

    def test_blank_rows_are_ignored_and_limits_apply_to_pasted_and_manual_input(self):
        self.assertEqual(len(load_pasted("\n\t\t\n6\t80\t70\n\n")), 1)
        with patch("messi.data.MAX_ROWS", 1), self.assertRaises(ValidationError):
            load_pasted("6;80;70\n7;90;90\n")
        with patch("messi.data.MAX_BYTES", 5), self.assertRaises(ValidationError):
            load_pasted("6;80;70\n")


if __name__ == "__main__":
    unittest.main()
