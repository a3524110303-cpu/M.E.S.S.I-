"""Importación única y transaccional del SQLite anterior de MESSI."""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from messi.database import MySQLDatabase
from messi.storage import _student_id, _text, _choice, SUPPORT_STATUSES, SUPPORT_TYPES


class MigrationError(ValueError):
    pass


def _positive_id(value):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MigrationError("El SQLite contiene un identificador inválido.")
    return value


def _snapshot(source):
    source = Path(source).resolve()
    if not source.is_file():
        raise MigrationError("No se encontró la base SQLite anterior de MESSI.")
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as db:
            db.row_factory = sqlite3.Row
            db.execute("BEGIN")
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or db.execute("PRAGMA foreign_key_check").fetchone():
                raise MigrationError("La base SQLite no pasó las comprobaciones de integridad.")
            tablas = {fila[0] for fila in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            if not {"requests", "supports", "followups"}.issubset(tablas):
                raise MigrationError("El archivo no contiene el esquema SQLite de MESSI.")
            datos = {tabla: [dict(fila) for fila in db.execute(f"SELECT * FROM {tabla} ORDER BY id")]
                     for tabla in ("requests", "supports", "followups")}
            apoyos = {fila["id"] for fila in datos["supports"]}
            for tabla, filas in datos.items():
                for fila in filas:
                    _positive_id(fila["id"])
                    if len(fila["created_at"]) > 40:
                        raise MigrationError("La fecha guardada supera el tamaño permitido.")
                    datetime.fromisoformat(fila["created_at"])
                    if tabla != "followups":
                        _student_id(fila["student_id"])
                    if tabla == "requests":
                        _text(fila["message"], "El mensaje")
                    else:
                        _text(fila["notes"], "La nota")
                        _choice(fila["status"], SUPPORT_STATUSES, "El estado")
                    if tabla == "supports":
                        _choice(fila["support_type"], SUPPORT_TYPES, "El tipo de apoyo")
                    if tabla == "followups" and fila["support_id"] not in apoyos:
                        raise MigrationError("Un seguimiento no tiene su apoyo correspondiente.")
            return datos
    except (sqlite3.Error, KeyError, TypeError, ValueError) as error:
        if isinstance(error, MigrationError):
            raise
        raise MigrationError("No se pudo validar el SQLite de MESSI; el archivo original permanece intacto.") from error


def migrate_sqlite(source: Path, database: MySQLDatabase):
    datos = _snapshot(source)
    with database.connection() as db:
        # Serializa la migración con otras migraciones del mismo destino.
        db.execute("SELECT version FROM schema_migrations WHERE version = %s FOR UPDATE", (1,)).fetchone()
        if db.execute("SELECT version FROM schema_migrations WHERE version = %s", (2,)).fetchone():
            return {"already_applied": True}
        for tabla in ("requests", "supports", "followups"):
            # Bloquear el rango completo impide mezclar nuevas escrituras durante
            # la importación; connection() usa REPEATABLE READ para los gap locks.
            if db.execute(f"SELECT id FROM {tabla} WHERE id >= 0 FOR UPDATE").fetchall():
                raise MigrationError("La importación exige solicitudes, apoyos y seguimientos vacíos en el destino.")
        estudiantes = {}
        for tabla in ("requests", "supports"):
            for fila in datos[tabla]:
                estudiantes.setdefault(fila["student_id"], fila["created_at"])
        for estudiante, creada in sorted(estudiantes.items()):
            db.execute("INSERT INTO students(id, created_at) VALUES (%s, %s) ON DUPLICATE KEY UPDATE id = id",
                       (estudiante, creada))
        columnas = {
            "requests": ("id", "student_id", "message", "created_at"),
            "supports": ("id", "student_id", "support_type", "notes", "created_at", "status"),
            "followups": ("id", "support_id", "notes", "status", "created_at"),
        }
        for tabla, campos in columnas.items():
            for fila in datos[tabla]:
                db.execute(f"INSERT INTO {tabla}({', '.join(campos)}) VALUES ({', '.join(['%s'] * len(campos))})",
                           tuple(fila[campo] for campo in campos))
        db.execute("INSERT INTO schema_migrations(version, description, applied_at) VALUES (%s, %s, %s)",
                   (2, "Importación de SQLite MESSI", datetime.now(timezone.utc).isoformat()))
    return {tabla: len(filas) for tabla, filas in datos.items()}
