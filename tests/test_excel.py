"""Libros de prueba en memoria; no se escriben ni distribuyen archivos Excel."""

import importlib.util
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from messi.data import FRIENDLY_HEADERS, ValidationError, load_excel


_EXCEL_AVAILABLE = importlib.util.find_spec("openpyxl") is not None


@unittest.skipUnless(_EXCEL_AVAILABLE, "Pruebas Excel omitidas: instala openpyxl del proyecto.")
class ExcelInputTests(unittest.TestCase):
    def workbook_bytes(self, rows, title="Datos", extra_sheets=()):
        import openpyxl

        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = title
        for row in rows:
            sheet.append(row)
        for name in extra_sheets:
            workbook.create_sheet(name)
        output = io.BytesIO()
        workbook.save(output)
        workbook.close()
        return output.getvalue()

    def test_friendly_headers_blank_rows_and_temporary_ids(self):
        raw = self.workbook_bytes([
            FRIENDLY_HEADERS, [None, 6.5, 80, 70], [None, None, None, None],
            ["EST-0001", 8, 90, 95], ["", "4,5", 60, 40],
        ], extra_sheets=("Instrucciones",))
        records = load_excel(raw)
        self.assertEqual([row["id_estudiante"] for row in records], ["EST-0002", "EST-0001", "EST-0003"])
        self.assertEqual(records[-1]["nota_parcial"], 4.5)

    def test_only_sheet_is_allowed_without_datos_and_canonical_headers_work(self):
        raw = self.workbook_bytes([
            ["asistencia", "tareas_entregadas", "id_estudiante", "nota_parcial"], [80, 70, "EST-001", 6]
        ], title="Grupo A")
        self.assertEqual(load_excel(raw)[0]["nota_parcial"], 6.0)

    def test_ambiguous_sheets_are_rejected(self):
        raw = self.workbook_bytes([FRIENDLY_HEADERS, [None, 6, 80, 70]], title="Grupo A", extra_sheets=("Grupo B",))
        with self.assertRaisesRegex(ValidationError, "Datos"):
            load_excel(raw)

    def test_formulas_are_rejected_even_in_extra_cells(self):
        for row in ([None, "=6+1", 80, 70], [None, 6, 80, 70, "=1+1"]):
            with self.subTest(row=row):
                raw = self.workbook_bytes([FRIENDLY_HEADERS, row])
                with self.assertRaisesRegex(ValidationError, "fórmulas"):
                    load_excel(raw)

    def test_missing_duplicate_extra_headers_and_data_are_rejected(self):
        cases = (
            [FRIENDLY_HEADERS[:3], [None, 6, 80]],
            [["ID estudiante", "Nota primer parcial", "Asistencia (%)", "Asistencia (%)"], [None, 6, 80, 70]],
            [[*FRIENDLY_HEADERS, "nombre"], [None, 6, 80, 70, "Ana"]],
            [FRIENDLY_HEADERS, [None, 6, 80, 70, "Ana"]],
            [FRIENDLY_HEADERS, [None, None, 80, 70]],
            [FRIENDLY_HEADERS, [None, 11, 80, 70]],
            [FRIENDLY_HEADERS, ["Ana", 6, 80, 70]],
            [FRIENDLY_HEADERS, ["EST-001", 6, 80, 70], ["EST-001", 7, 90, 90]],
            [FRIENDLY_HEADERS],
        )
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValidationError):
                load_excel(self.workbook_bytes(rows))

    def test_byte_row_and_expansion_limits_apply(self):
        raw = self.workbook_bytes([FRIENDLY_HEADERS, [None, 6, 80, 70], [None, 7, 90, 90]])
        with patch("messi.data.MAX_BYTES", len(raw) - 1), self.assertRaises(ValidationError):
            load_excel(raw)
        with patch("messi.data.MAX_ROWS", 1), self.assertRaises(ValidationError):
            load_excel(raw)
        with patch("messi.data.MAX_XLSX_EXPANDED_BYTES", 1), self.assertRaises(ValidationError):
            load_excel(raw)


class ExcelEnvelopeTests(unittest.TestCase):
    def test_invalid_and_empty_workbooks_are_rejected_without_optional_import(self):
        for raw in (b"", b"esto no es un Excel", "archivo.xlsx"):
            with self.subTest(raw=raw), self.assertRaises(ValidationError):
                load_excel(raw)


if __name__ == "__main__":
    unittest.main()
