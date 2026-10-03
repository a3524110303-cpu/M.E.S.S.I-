"""Contrato de datos de MESSI, sin dependencias de aprendizaje automático."""

from __future__ import annotations

import csv
import io
import math
import re
from pathlib import Path
from zipfile import BadZipFile, ZipFile

FEATURES = ("nota_parcial", "asistencia", "tareas_entregadas")
ID_COLUMN = "id_estudiante"
TARGET = "resultado_final"
MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 10_000
MAX_XLSX_EXPANDED_BYTES = 50 * 1024 * 1024
FRIENDLY_HEADERS = (
    "ID estudiante", "Nota primer parcial", "Asistencia (%)", "Tareas entregadas (%)"
)
_INPUT_COLUMNS = (ID_COLUMN, *FEATURES)
_HEADER_MAP = dict(zip(FRIENDLY_HEADERS, _INPUT_COLUMNS, strict=True))
_HEADER_MAP.update({column: column for column in _INPUT_COLUMNS})
_ID_PATTERN = re.compile(r"EST-[0-9]{3,8}\Z")


class ValidationError(ValueError):
    """El archivo no cumple el contrato mínimo de datos."""


def _read_source(source: bytes | str | Path) -> str:
    try:
        if isinstance(source, Path):
            if source.stat().st_size > MAX_BYTES:
                raise ValidationError("El CSV supera el límite de 5 MB.")
            raw = source.read_bytes()
        elif isinstance(source, bytes):
            raw = source
        elif isinstance(source, str):
            raw = source.encode("utf-8")
        else:
            raise ValidationError("Proporciona bytes, contenido de texto o un Path.")
    except OSError as exc:
        raise ValidationError("No se pudo leer el archivo CSV.") from exc
    except UnicodeEncodeError as exc:
        raise ValidationError("El CSV debe usar texto UTF-8 válido.") from exc
    if len(raw) > MAX_BYTES:
        raise ValidationError("El CSV supera el límite de 5 MB.")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationError("El CSV debe estar codificado en UTF-8.") from exc


def _coerce_record(row: dict, row_number: int, training: bool) -> dict:
    expected = {ID_COLUMN, *FEATURES}
    if training:
        expected.add(TARGET)
    if set(row) != expected:
        raise ValidationError(f"Fila {row_number}: columnas incompletas o no permitidas.")
    student_id = str(row.get(ID_COLUMN, "")).strip()
    if not _ID_PATTERN.fullmatch(student_id):
        raise ValidationError(
            f"Fila {row_number}: usa un identificador anónimo EST- con 3 a 8 dígitos."
        )
    normalized = {ID_COLUMN: student_id}
    for name in FEATURES:
        raw_value = row.get(name)
        if raw_value is None or isinstance(raw_value, bool):
            raise ValidationError(f"Fila {row_number}: {name} está vacío o es inválido.")
        raw_text = str(raw_value).strip()
        if not raw_text:
            raise ValidationError(f"Fila {row_number}: {name} está vacío.")
        try:
            value = float(raw_text)
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValidationError(f"Fila {row_number}: {name} debe ser numérico.") from exc
        upper_bound = 10.0 if name == "nota_parcial" else 100.0
        if not math.isfinite(value) or not 0.0 <= value <= upper_bound:
            raise ValidationError(
                f"Fila {row_number}: {name} debe estar entre 0 y {upper_bound:g}."
            )
        normalized[name] = value
    if training:
        raw_target = str(row.get(TARGET, "")).strip()
        if raw_target not in ("0", "1"):
            raise ValidationError(
                f"Fila {row_number}: resultado_final debe ser 0 (aprobado) o 1 (reprobado)."
            )
        normalized[TARGET] = int(raw_target)
    return normalized


def load_csv(source: bytes | str | Path, training: bool = False) -> list[dict]:
    """Valida CSV UTF-8 y devuelve registros normalizados.

    Un str se interpreta como contenido CSV; para una ruta usa pathlib.Path.
    Los porcentajes se expresan de 0 a 100, la nota de 0 a 10.
    resultado_final sólo se admite con training=True y nunca es una entrada IA.
    """
    contents = _read_source(source)
    if not contents.strip():
        raise ValidationError("El CSV está vacío.")
    expected = {ID_COLUMN, *FEATURES}
    if training:
        expected.add(TARGET)
    reader = csv.DictReader(io.StringIO(contents, newline=""), strict=True)
    try:
        headers = reader.fieldnames
        if not headers:
            raise ValidationError("El CSV requiere una fila de encabezados.")
        if len(headers) != len(set(headers)):
            raise ValidationError("El CSV contiene encabezados duplicados.")
        extras = set(headers) - expected
        missing = expected - set(headers)
        if extras:
            raise ValidationError(
                "Hay columnas no permitidas. Usa sólo: " + ", ".join(sorted(expected)) + "."
            )
        if missing:
            raise ValidationError("Faltan columnas: " + ", ".join(sorted(missing)) + ".")
        records: list[dict] = []
        seen_ids: set[str] = set()
        for row_number, row in enumerate(reader, start=2):
            if len(records) >= MAX_ROWS:
                raise ValidationError("El CSV supera el límite de 10,000 estudiantes.")
            if None in row or any(value is None for value in row.values()):
                raise ValidationError(f"Fila {row_number}: cantidad incorrecta de campos.")
            record = _coerce_record(row, row_number, training)
            student_id = record[ID_COLUMN]
            if student_id in seen_ids:
                raise ValidationError(f"Fila {row_number}: identificador anónimo duplicado.")
            seen_ids.add(student_id)
            records.append(record)
    except csv.Error as exc:
        raise ValidationError("El CSV tiene un formato inválido.") from exc
    if not records:
        raise ValidationError("El CSV requiere al menos un estudiante.")
    return records


def validate_records(records: list[dict]) -> list[dict]:
    """Valida registros canónicos de inferencia sin agregar columnas ni etiquetas.

    Los IDs son obligatorios en esta API; load_excel y load_pasted generan IDs
    temporales para las modalidades que permiten omitirlos.
    """
    if not isinstance(records, list) or not records:
        raise ValidationError("Ingresa al menos un estudiante.")
    if len(records) > MAX_ROWS:
        raise ValidationError("Se supera el límite de 10,000 estudiantes.")
    normalized = []
    seen_ids: set[str] = set()
    for row_number, record in enumerate(records, start=2):
        if not isinstance(record, dict):
            raise ValidationError(f"Fila {row_number}: registro inválido.")
        clean = _coerce_record(record, row_number, training=False)
        if clean[ID_COLUMN] in seen_ids:
            raise ValidationError(f"Fila {row_number}: identificador anónimo duplicado.")
        seen_ids.add(clean[ID_COLUMN])
        normalized.append(clean)
    return normalized


def record_from_counts(
    student_id: str,
    nota_parcial: float,
    asistencias: int,
    sesiones: int,
    tareas_entregadas: int,
    tareas_solicitadas: int,
) -> dict:
    """Convierte conteos de captura manual en los porcentajes del contrato.

    Los totales deben ser enteros positivos y lo realizado no puede superar
    lo solicitado. Se conserva la precisión de las divisiones, sin redondear.
    """
    counts = {
        "asistencias": asistencias, "sesiones": sesiones,
        "tareas_entregadas": tareas_entregadas, "tareas_solicitadas": tareas_solicitadas,
    }
    for name, value in counts.items():
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValidationError(f"{name} debe ser un número entero.")
    if sesiones <= 0 or tareas_solicitadas <= 0:
        raise ValidationError("El total de sesiones y tareas solicitadas debe ser mayor que cero.")
    if not 0 <= asistencias <= sesiones:
        raise ValidationError("Las asistencias deben estar entre cero y el total de sesiones.")
    if not 0 <= tareas_entregadas <= tareas_solicitadas:
        raise ValidationError("Las tareas entregadas deben estar entre cero y las tareas solicitadas.")
    return validate_records([
        {
            ID_COLUMN: student_id,
            "nota_parcial": nota_parcial,
            "asistencia": 100 * asistencias / sesiones,
            "tareas_entregadas": 100 * tareas_entregadas / tareas_solicitadas,
        }
    ])[0]


def _is_empty(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _trim_trailing_empty(values: list) -> list:
    values = list(values)
    while values and _is_empty(values[-1]):
        values.pop()
    return values


def _normalize_headers(values: list) -> list[str]:
    headers = [str(value).strip() if value is not None else "" for value in values]
    if len(headers) != 4 or any(header not in _HEADER_MAP for header in headers):
        raise ValidationError(
            "Usa las cuatro columnas de la plantilla: " + ", ".join(FRIENDLY_HEADERS) + "."
        )
    normalized = [_HEADER_MAP[header] for header in headers]
    if len(normalized) != len(set(normalized)):
        raise ValidationError("Hay encabezados duplicados.")
    if set(normalized) != set(_INPUT_COLUMNS):
        raise ValidationError("Faltan columnas requeridas de la plantilla.")
    return normalized


def _decimal_value(value):
    # Sólo el pegado/Excel permite coma decimal; CSV conserva su contrato con punto.
    if isinstance(value, str):
        text = value.strip()
        if text.count(",") == 1 and "." not in text:
            return text.replace(",", ".")
        return text
    return value


def _fill_temporary_ids(records: list[dict]) -> list[dict]:
    # Reserva también IDs de filas posteriores antes de generar los temporales.
    used_ids = {
        str(row[ID_COLUMN]).strip() for row in records if not _is_empty(row[ID_COLUMN])
    }
    candidate_number = 1
    normalized = []
    for row in records:
        record = dict(row)
        if _is_empty(record[ID_COLUMN]):
            while f"EST-{candidate_number:04d}" in used_ids:
                candidate_number += 1
            generated_id = f"EST-{candidate_number:04d}"
            record[ID_COLUMN] = generated_id
            used_ids.add(generated_id)
            candidate_number += 1
        for feature in FEATURES:
            record[feature] = _decimal_value(record[feature])
        normalized.append(record)
    return validate_records(normalized)


def load_pasted(text: str) -> list[dict]:
    """Lee una tabla pegada con tabuladores o punto y coma.

    Con encabezados se requieren las cuatro columnas amigables o canónicas.
    Sin encabezados: tres columnas (nota, asistencia, tareas) o cuatro (ID y
    las tres variables). Los IDs vacíos reciben identificadores temporales.
    Se admite coma decimal; la coma nunca se interpreta como delimitador.
    """
    if not isinstance(text, str):
        raise ValidationError("Pega una tabla de texto.")
    contents = _read_source(text)
    if not contents.strip():
        raise ValidationError("Pega al menos una fila de datos.")
    has_tabs, has_semicolons = "\t" in contents, ";" in contents
    if has_tabs and has_semicolons:
        raise ValidationError("Usa un solo separador: tabuladores o punto y coma.")
    if not has_tabs and not has_semicolons:
        raise ValidationError("Separa las columnas con tabuladores o punto y coma; no con comas.")
    delimiter = "\t" if has_tabs else ";"
    reader = csv.reader(io.StringIO(contents, newline=""), delimiter=delimiter, strict=True)
    headers = None
    columns = None
    records = []
    try:
        for row_number, row in enumerate(reader, start=1):
            if not row or all(_is_empty(value) for value in row):
                continue
            if columns is None:
                first_values = [value.strip() for value in row]
                if any(value in _HEADER_MAP or value == TARGET for value in first_values):
                    headers = _normalize_headers(row)
                    columns = headers
                    continue
                if len(row) == 3:
                    columns = FEATURES
                elif len(row) == 4:
                    columns = _INPUT_COLUMNS
                else:
                    raise ValidationError("Cada fila pegada debe tener 3 o 4 columnas.")
            if len(row) != len(columns):
                raise ValidationError(f"Fila {row_number}: cantidad incorrecta de columnas.")
            if len(records) >= MAX_ROWS:
                raise ValidationError("Se supera el límite de 10,000 estudiantes.")
            record = dict(zip(columns, row, strict=True))
            record.setdefault(ID_COLUMN, "")
            records.append(record)
    except csv.Error as exc:
        raise ValidationError("La tabla pegada tiene un formato inválido.") from exc
    return _fill_temporary_ids(records)


def load_excel(source: bytes | Path) -> list[dict]:
    """Lee .xlsx con openpyxl opcional y devuelve el mismo contrato que CSV.

    Usa la hoja Datos o, si no existe, la única hoja del libro. Encabezados en
    fila 1; cuatro columnas amigables o canónicas; porcentajes numéricos 0–100.
    Las filas totalmente vacías se ignoran y los IDs vacíos son temporales.
    Las fórmulas se rechazan incluso si Excel contiene resultados almacenados.
    """
    try:
        if isinstance(source, Path):
            if source.stat().st_size > MAX_BYTES:
                raise ValidationError("El archivo Excel supera el límite de 5 MB.")
            raw = source.read_bytes()
        elif isinstance(source, bytes):
            raw = source
        else:
            raise ValidationError("Proporciona bytes o un Path de un archivo .xlsx.")
    except OSError as exc:
        raise ValidationError("No se pudo leer el archivo Excel.") from exc
    if not raw:
        raise ValidationError("El archivo Excel está vacío.")
    if len(raw) > MAX_BYTES:
        raise ValidationError("El archivo Excel supera el límite de 5 MB.")
    try:
        with ZipFile(io.BytesIO(raw)) as archive:
            if sum(entry.file_size for entry in archive.infolist()) > MAX_XLSX_EXPANDED_BYTES:
                raise ValidationError("El contenido del archivo Excel supera el tamaño admitido.")
    except BadZipFile as exc:
        raise ValidationError("El archivo debe ser un libro Excel .xlsx válido.") from exc
    try:
        import openpyxl
    except ImportError as exc:
        raise ValidationError("Falta openpyxl. Ejecuta INSTALAR_MESSI.bat para leer archivos Excel.") from exc

    workbook = None
    try:
        workbook = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=False, keep_links=False)
        if "Datos" in workbook.sheetnames:
            sheet = workbook["Datos"]
        elif len(workbook.sheetnames) == 1:
            sheet = workbook[workbook.sheetnames[0]]
        else:
            raise ValidationError("Usa una hoja llamada Datos o un libro con una sola hoja.")
        # También limita dimensiones físicas para no recorrer libros con millones de celdas vacías.
        if sheet.max_row and sheet.max_row > MAX_ROWS + 1:
            raise ValidationError("La hoja Excel supera el límite de 10,000 filas de datos.")
        if sheet.max_column and sheet.max_column > 100:
            raise ValidationError("La hoja Excel contiene demasiadas columnas; usa la plantilla de 4 columnas.")
        headers = None
        records = []
        for row_number, cells in enumerate(sheet.iter_rows(), start=1):
            if any(cell.data_type == "f" for cell in cells):
                raise ValidationError(f"Fila {row_number}: usa valores numéricos; no se admiten fórmulas.")
            values = [cell.value for cell in cells]
            if row_number == 1:
                headers = _normalize_headers(_trim_trailing_empty(values))
                continue
            if all(_is_empty(value) for value in values):
                continue
            if headers is None:
                raise ValidationError("Faltan los encabezados en la primera fila de Excel.")
            if any(not _is_empty(value) for value in values[len(headers):]):
                raise ValidationError(f"Fila {row_number}: hay columnas adicionales no permitidas.")
            if len(records) >= MAX_ROWS:
                raise ValidationError("Se supera el límite de 10,000 estudiantes.")
            row_values = values[:len(headers)]
            row_values.extend([None] * (len(headers) - len(row_values)))
            records.append(dict(zip(headers, row_values, strict=True)))
        return _fill_temporary_ids(records)
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError("No se pudo abrir el libro .xlsx. Revisa su formato y usa la plantilla.") from exc
    finally:
        if workbook is not None:
            workbook.close()
