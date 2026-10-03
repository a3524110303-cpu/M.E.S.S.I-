"""Solicitudes, apoyos y seguimientos locales para la demostración de MESSI.

El identificador EST-000 identifica un registro sintético, no una cuenta ni una
identidad autenticada. La interfaz de esta entrega debe usar datos de ejemplo.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import re
import sqlite3
from typing import Iterator


SUPPORT_TYPES = ("Tutoria", "Apoyo accesible", "Orientacion")
SUPPORT_STATUSES = ("Pendiente", "En seguimiento", "Cerrado")
_STUDENT_ID = re.compile(r"EST-[0-9]{3,8}")
_TEXT_LIMIT = 1000


def _student_id(value: str) -> str:
    if not isinstance(value, str) or not _STUDENT_ID.fullmatch(value.strip()):
        raise ValueError("El identificador debe tener el formato EST- seguido de 3 a 8 dígitos.")
    return value.strip()


def _text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} no puede estar vacío.")
    value = value.strip()
    if len(value) > _TEXT_LIMIT:
        raise ValueError(f"{label} debe tener como máximo {_TEXT_LIMIT} caracteres.")
    return value


def _choice(value: str, choices: tuple[str, ...], label: str) -> str:
    if not isinstance(value, str) or value.strip() not in choices:
        raise ValueError(f"{label} debe ser uno de estos valores: {', '.join(choices)}.")
    return value.strip()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SupportStore:
    """Persistencia SQLite; cada operación abre y cierra su propia conexión.

    En la aplicación, usar ``data/private/messi.sqlite3`` y excluir esa carpeta
    de Git. Una solicitud puede registrarse sin cargar datos ni hacer una
    predicción. Los identificadores no se verifican contra un archivo externo.
    """

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    message TEXT NOT NULL CHECK(length(trim(message)) BETWEEN 1 AND 1000),
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS supports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    support_type TEXT NOT NULL
                        CHECK(support_type IN ('Tutoria', 'Apoyo accesible', 'Orientacion')),
                    notes TEXT NOT NULL CHECK(length(trim(notes)) BETWEEN 1 AND 1000),
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Pendiente'
                        CHECK(status IN ('Pendiente', 'En seguimiento', 'Cerrado'))
                );
                CREATE TABLE IF NOT EXISTS followups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    support_id INTEGER NOT NULL REFERENCES supports(id),
                    notes TEXT NOT NULL CHECK(length(trim(notes)) BETWEEN 1 AND 1000),
                    status TEXT NOT NULL
                        CHECK(status IN ('Pendiente', 'En seguimiento', 'Cerrado')),
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS requests_student ON requests(student_id);
                CREATE INDEX IF NOT EXISTS supports_student ON supports(student_id);
                CREATE INDEX IF NOT EXISTS followups_support ON followups(support_id);
                """
            )

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def create_request(self, student_id: str, message: str) -> int:
        student_id = _student_id(student_id)
        message = _text(message, "El mensaje")
        with self._connection() as connection:
            cursor = connection.execute(
                "INSERT INTO requests(student_id, message, created_at) VALUES (?, ?, ?)",
                (student_id, message, _utc_now()),
            )
            return int(cursor.lastrowid)

    def list_requests(self, student_id: str | None = None) -> list[dict]:
        if student_id is not None:
            student_id = _student_id(student_id)
        with self._connection() as connection:
            if student_id is None:
                rows = connection.execute("SELECT * FROM requests ORDER BY id DESC").fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM requests WHERE student_id = ? ORDER BY id DESC",
                    (student_id,),
                ).fetchall()
            return [dict(row) for row in rows]

    def create_support(self, student_id: str, support_type: str, notes: str) -> int:
        student_id = _student_id(student_id)
        support_type = _choice(support_type, SUPPORT_TYPES, "El tipo de apoyo")
        notes = _text(notes, "La nota")
        with self._connection() as connection:
            cursor = connection.execute(
                "INSERT INTO supports(student_id, support_type, notes, created_at, status) "
                "VALUES (?, ?, ?, ?, ?)",
                (student_id, support_type, notes, _utc_now(), "Pendiente"),
            )
            return int(cursor.lastrowid)

    def list_supports(self, student_id: str | None = None) -> list[dict]:
        if student_id is not None:
            student_id = _student_id(student_id)
        with self._connection() as connection:
            if student_id is None:
                rows = connection.execute("SELECT * FROM supports ORDER BY id DESC").fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM supports WHERE student_id = ? ORDER BY id DESC",
                    (student_id,),
                ).fetchall()
            return [dict(row) for row in rows]

    def add_followup(self, support_id: int, notes: str, status: str) -> int:
        support_id = self._support_id(support_id)
        notes = _text(notes, "La nota de seguimiento")
        status = _choice(status, SUPPORT_STATUSES, "El estado")
        with self._connection() as connection:
            # El cambio de estado y su registro se guardan en una transacción.
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "UPDATE supports SET status = ? WHERE id = ?", (status, support_id)
            )
            if cursor.rowcount != 1:
                raise ValueError("El apoyo indicado no existe.")
            cursor = connection.execute(
                "INSERT INTO followups(support_id, notes, status, created_at) VALUES (?, ?, ?, ?)",
                (support_id, notes, status, _utc_now()),
            )
            return int(cursor.lastrowid)

    def list_followups(self, support_id: int) -> list[dict]:
        support_id = self._support_id(support_id)
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM followups WHERE support_id = ? ORDER BY id DESC", (support_id,)
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def _support_id(value: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError("El identificador del apoyo debe ser un entero positivo.")
        return value
