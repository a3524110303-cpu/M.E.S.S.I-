"""La importación institucional no inventa la identidad de un estudiante."""
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from openpyxl import Workbook
from messi.data import ValidationError, load_excel


class RegisteredExcelIDTests(unittest.TestCase):
    def workbook(self, code):
        book = Workbook()
        book.active.title = "Datos"
        book.active.append(["id_estudiante", "nota_parcial", "asistencia", "tareas_entregadas"])
        book.active.append([code, "7,5", 80, 90])
        output = io.BytesIO()
        book.save(output)
        book.close()
        return output.getvalue()

    def test_institutional_import_rejects_blank_student_ids(self):
        for code in (None, "", "   "):
            with self.subTest(code=code), self.assertRaisesRegex(ValidationError, "código del estudiante inscrito"):
                load_excel(self.workbook(code), allow_temporary_ids=False)

    def test_institutional_import_preserves_explicit_registered_id(self):
        records = load_excel(self.workbook("EST-001"), allow_temporary_ids=False)
        self.assertEqual(records, [{"id_estudiante": "EST-001", "nota_parcial": 7.5, "asistencia": 80.0, "tareas_entregadas": 90.0}])

    def test_local_demo_still_generates_temporary_ids_by_default(self):
        self.assertEqual(load_excel(self.workbook(None))[0]["id_estudiante"], "EST-0001")
