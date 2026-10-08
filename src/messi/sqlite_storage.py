"""Almacenamiento completo de MESSI en SQLite, sin servicio ni credenciales."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3

from messi.data import FEATURES, ID_COLUMN, ValidationError, validate_records
from messi.database import DatabaseError
from messi.storage import SupportStore, _student_id, _text, _utc_now
from messi.storage_validation import _period, _prediction_records


class SQLiteStore(SupportStore):
    """Amplía SQLite legado conservando solicitudes, apoyos e IDs existentes."""

    def __init__(self, db_path: Path):
        try:
            self.db_path = Path(db_path)
            if self.db_path.exists():
                with self._connection() as db:
                    if db.execute("PRAGMA user_version").fetchone()[0] > 1:
                        raise DatabaseError("Esta base requiere una versión más reciente de MESSI.")
            super().__init__(db_path)
            with self._connection() as db:
                version = db.execute("PRAGMA user_version").fetchone()[0]
                if version > 1:
                    raise DatabaseError("Esta base requiere una versión más reciente de MESSI.")
                db.execute("PRAGMA journal_mode=WAL")
                db.executescript("""
                    CREATE TABLE IF NOT EXISTS students (
                        id TEXT PRIMARY KEY, created_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS indicators (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id TEXT NOT NULL REFERENCES students(id),
                        period TEXT NOT NULL CHECK(length(trim(period)) BETWEEN 1 AND 64),
                        nota_parcial REAL NOT NULL CHECK(nota_parcial BETWEEN 0 AND 10),
                        asistencia REAL NOT NULL CHECK(asistencia BETWEEN 0 AND 100),
                        tareas_entregadas REAL NOT NULL CHECK(tareas_entregadas BETWEEN 0 AND 100),
                        updated_at TEXT NOT NULL,
                        UNIQUE(student_id, period)
                    );
                    CREATE TABLE IF NOT EXISTS predictions (
                        indicator_id INTEGER PRIMARY KEY REFERENCES indicators(id) ON DELETE CASCADE,
                        puntuacion_riesgo REAL NOT NULL CHECK(puntuacion_riesgo BETWEEN 0 AND 1),
                        alerta INTEGER NOT NULL CHECK(alerta IN (0,1)),
                        origen_modelo TEXT NOT NULL CHECK(length(trim(origen_modelo)) BETWEEN 1 AND 100),
                        created_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS indicators_period ON indicators(period, student_id);
                    PRAGMA user_version=1;
                """)
                for tabla in ("requests", "supports"):
                    db.execute(f"INSERT OR IGNORE INTO students SELECT student_id, MIN(created_at) FROM {tabla} GROUP BY student_id")
        except OSError as exc:
            raise DatabaseError("No puedo crear la base local. Comprueba el espacio y los permisos de la carpeta de datos.") from exc

    @contextmanager
    def _connection(self):
        try:
            with super()._connection() as db:
                yield db
        except sqlite3.Error as exc:
            raise DatabaseError("No pude acceder a SQLite. Comprueba el espacio, los permisos y que el respaldo sea válido.") from exc

    @staticmethod
    def _ensure_student(db, student_id, now):
        db.execute("INSERT OR IGNORE INTO students VALUES (?,?)", (student_id, now))

    def create_request(self, student_id: str, message: str) -> int:
        """Validar y guardar una solicitud de ayuda; devolver su identificador."""
        student_id = _student_id(student_id)
        message = _text(message, "El mensaje")
        now = _utc_now()
        with self._connection() as db:
            self._ensure_student(db, student_id, now)
            return int(db.execute("INSERT INTO requests(student_id,message,created_at) VALUES (?,?,?)",
                                 (student_id, message, now)).lastrowid)

    def create_support(self, student_id: str, support_type: str, notes: str) -> int:
        """Guardar un apoyo validado con estado inicial Pendiente y devolver su ID."""
        from messi.storage import _choice, SUPPORT_TYPES
        student_id = _student_id(student_id)
        support_type = _choice(support_type, SUPPORT_TYPES, "El tipo de apoyo")
        notes = _text(notes, "La nota")
        now = _utc_now()
        with self._connection() as db:
            self._ensure_student(db, student_id, now)
            return int(db.execute("INSERT INTO supports(student_id,support_type,notes,created_at,status) VALUES (?,?,?,?,?)",
                                 (student_id, support_type, notes, now, "Pendiente")).lastrowid)

    @staticmethod
    def _indicator(db, student_id, period):
        return db.execute("SELECT * FROM indicators WHERE student_id=? AND period=?", (student_id, period)).fetchone()

    @staticmethod
    def _same(stored, record):
        return all(float(stored[feature]) == record[feature] for feature in FEATURES)

    @staticmethod
    def _upsert_indicator(db, record, period, now):
        db.execute("""INSERT INTO indicators(student_id,period,nota_parcial,asistencia,tareas_entregadas,updated_at)
            VALUES (?,?,?,?,?,?) ON CONFLICT(student_id,period) DO UPDATE SET
            nota_parcial=excluded.nota_parcial, asistencia=excluded.asistencia,
            tareas_entregadas=excluded.tareas_entregadas, updated_at=excluded.updated_at""",
            (record[ID_COLUMN], period, *(record[name] for name in FEATURES), now))

    def save_indicators(self, records: list[dict], period: str = "primer_parcial") -> int:
        """Guardar un lote validado por periodo e invalidar predicciones si cambian sus entradas."""
        records = validate_records(records)
        period = _period(period)
        now = _utc_now()
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            for record in records:
                self._ensure_student(db, record[ID_COLUMN], now)
                anterior = self._indicator(db, record[ID_COLUMN], period)
                if anterior is not None and not self._same(anterior, record):
                    db.execute("DELETE FROM predictions WHERE indicator_id=?", (anterior["id"],))
                self._upsert_indicator(db, record, period, now)
        return len(records)

    def list_indicators(self, period: str = "primer_parcial") -> list[dict]:
        """Recuperar las tres variables académicas y el código para un periodo."""
        period = _period(period)
        with self._connection() as db:
            rows = db.execute("SELECT student_id AS id_estudiante, nota_parcial, asistencia, tareas_entregadas FROM indicators WHERE period=? ORDER BY student_id", (period,)).fetchall()
        return [dict(row) for row in rows]

    def save_predictions(self, records: list[dict], period: str = "primer_parcial") -> int:
        """Persistir puntuaciones sólo si coinciden con los indicadores vigentes; devolver el total."""
        records = _prediction_records(records)
        period = _period(period)
        now = _utc_now()
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            for record in records:
                self._ensure_student(db, record[ID_COLUMN], now)
                anterior = self._indicator(db, record[ID_COLUMN], period)
                if anterior is not None and not self._same(anterior, record):
                    raise ValidationError(f"Los indicadores de {record[ID_COLUMN]} cambiaron. Recarga los datos y vuelve a calcular.")
                if anterior is None:
                    self._upsert_indicator(db, record, period, now)
                    anterior = self._indicator(db, record[ID_COLUMN], period)
                db.execute("""INSERT INTO predictions VALUES (?,?,?,?,?)
                    ON CONFLICT(indicator_id) DO UPDATE SET puntuacion_riesgo=excluded.puntuacion_riesgo,
                    alerta=excluded.alerta, origen_modelo=excluded.origen_modelo, created_at=excluded.created_at""",
                    (anterior["id"], record["puntuacion_riesgo"], int(record["alerta"]), record["origen_modelo"], now))
        return len(records)

    def list_predictions(self, period: str = "primer_parcial") -> list[dict]:
        """Recuperar indicadores y puntuaciones persistidos, con alerta booleana, por periodo."""
        period = _period(period)
        with self._connection() as db:
            rows = db.execute("""SELECT i.student_id AS id_estudiante,i.nota_parcial,i.asistencia,
                i.tareas_entregadas,p.puntuacion_riesgo,p.alerta,p.origen_modelo
                FROM predictions p JOIN indicators i ON i.id=p.indicator_id
                WHERE i.period=? ORDER BY i.student_id""", (period,)).fetchall()
        return [{**dict(row), "alerta": bool(row["alerta"])} for row in rows]

    def backup(self, destination: Path):
        """Crear una copia consistente mediante SQLite backup en un archivo distinto a la base."""
        destination = Path(destination).resolve()
        if destination == self.db_path.resolve():
            raise ValueError("El respaldo debe guardarse en otro archivo.")
        try:
            with self._connection() as source:
                target = sqlite3.connect(destination)
                try:
                    source.backup(target)
                finally:
                    target.close()
        except (sqlite3.Error, OSError) as exc:
            raise DatabaseError("No pude guardar el respaldo SQLite.") from exc
