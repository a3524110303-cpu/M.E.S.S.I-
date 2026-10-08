"""Persistencia relacional de solicitudes, indicadores y predicciones en MySQL."""

from __future__ import annotations

from messi.data import FEATURES, ID_COLUMN, ValidationError, validate_records
from messi.database import MySQLDatabase
from messi.storage import (
    SUPPORT_STATUSES, SUPPORT_TYPES, _choice, _student_id, _text, _utc_now,
)


from messi.storage_validation import _period, _support_id, _prediction_records


class MySQLStore:
    """Abre una transacción por operación y conserva el contrato de SupportStore.

    La construcción no abre conexiones. Los indicadores se separan por periodo;
    una predicción sólo puede guardarse para los valores con los que se calculó.
    """

    def __init__(self, config):
        self.database = MySQLDatabase(config)

    def _connection(self):
        return self.database.connection()

    @staticmethod
    def _ensure_student(connection, student_id: str, now: str):
        # El upsert bloquea también el estudiante existente hasta el commit.
        # Todos los lotes siguen el mismo orden de IDs para evitar interbloqueos.
        connection.execute(
            "INSERT INTO students(id, created_at) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE id = id",
            (student_id, now),
        )

    def create_request(self, student_id: str, message: str) -> int:
        """Validar y guardar una solicitud de ayuda; devolver su identificador."""
        student_id = _student_id(student_id)
        message = _text(message, "El mensaje")
        now = _utc_now()
        with self._connection() as connection:
            self._ensure_student(connection, student_id, now)
            cursor = connection.execute(
                "INSERT INTO requests(student_id, message, created_at) VALUES (%s, %s, %s)",
                (student_id, message, now),
            )
            return int(cursor.lastrowid)

    def list_requests(self, student_id: str | None = None) -> list[dict]:
        """Recuperar solicitudes, opcionalmente filtradas por código de estudiante."""
        if student_id is not None:
            student_id = _student_id(student_id)
        with self._connection() as connection:
            if student_id is None:
                rows = connection.execute("SELECT * FROM requests ORDER BY id DESC").fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM requests WHERE student_id = %s ORDER BY id DESC", (student_id,)
                ).fetchall()
        return [dict(row) for row in rows]

    def create_support(self, student_id: str, support_type: str, notes: str) -> int:
        """Guardar un apoyo validado con estado inicial Pendiente y devolver su ID."""
        student_id = _student_id(student_id)
        support_type = _choice(support_type, SUPPORT_TYPES, "El tipo de apoyo")
        notes = _text(notes, "La nota")
        now = _utc_now()
        with self._connection() as connection:
            self._ensure_student(connection, student_id, now)
            cursor = connection.execute(
                "INSERT INTO supports(student_id, support_type, notes, created_at, status) "
                "VALUES (%s, %s, %s, %s, %s)",
                (student_id, support_type, notes, now, "Pendiente"),
            )
            return int(cursor.lastrowid)

    def list_supports(self, student_id: str | None = None) -> list[dict]:
        """Consultar apoyos en orden reciente, con filtro opcional de estudiante."""
        if student_id is not None:
            student_id = _student_id(student_id)
        with self._connection() as connection:
            if student_id is None:
                rows = connection.execute("SELECT * FROM supports ORDER BY id DESC").fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM supports WHERE student_id = %s ORDER BY id DESC", (student_id,)
                ).fetchall()
        return [dict(row) for row in rows]

    def add_followup(self, support_id: int, notes: str, status: str) -> int:
        """Guardar el seguimiento y actualizar el estado del apoyo en una transacción."""
        support_id = _support_id(support_id)
        notes = _text(notes, "La nota de seguimiento")
        status = _choice(status, SUPPORT_STATUSES, "El estado")
        with self._connection() as connection:
            support = connection.execute(
                "SELECT id FROM supports WHERE id = %s FOR UPDATE", (support_id,)
            ).fetchone()
            if support is None:
                raise ValueError("El apoyo indicado no existe.")
            connection.execute("UPDATE supports SET status = %s WHERE id = %s", (status, support_id))
            cursor = connection.execute(
                "INSERT INTO followups(support_id, notes, status, created_at) VALUES (%s, %s, %s, %s)",
                (support_id, notes, status, _utc_now()),
            )
            return int(cursor.lastrowid)

    def list_followups(self, support_id: int) -> list[dict]:
        """Listar las notas de seguimiento del apoyo indicado, de más reciente a antigua."""
        support_id = _support_id(support_id)
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM followups WHERE support_id = %s ORDER BY id DESC", (support_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _locked_indicator(connection, student_id: str, period: str):
        return connection.execute(
            "SELECT id, nota_parcial, asistencia, tareas_entregadas FROM indicators "
            "WHERE student_id = %s AND period = %s FOR UPDATE",
            (student_id, period),
        ).fetchone()

    @staticmethod
    def _same_indicators(stored: dict, record: dict) -> bool:
        return all(float(stored[feature]) == record[feature] for feature in FEATURES)

    @staticmethod
    def _upsert_indicator(connection, record: dict, period: str, now: str):
        return connection.execute(
            "INSERT INTO indicators(student_id, period, nota_parcial, asistencia, tareas_entregadas, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE "
            "nota_parcial = VALUES(nota_parcial), asistencia = VALUES(asistencia), "
            "tareas_entregadas = VALUES(tareas_entregadas), updated_at = VALUES(updated_at)",
            (record[ID_COLUMN], period, *(record[feature] for feature in FEATURES), now),
        )

    def save_indicators(self, records: list[dict], period: str = "primer_parcial") -> int:
        """Guardar un lote validado por periodo e invalidar predicciones si cambian sus entradas."""
        records = validate_records(records)
        period = _period(period)
        now = _utc_now()
        with self._connection() as connection:
            for record in sorted(records, key=lambda row: row[ID_COLUMN]):
                student_id = record[ID_COLUMN]
                self._ensure_student(connection, student_id, now)
                previous = self._locked_indicator(connection, student_id, period)
                if previous is not None and not self._same_indicators(previous, record):
                    connection.execute("DELETE FROM predictions WHERE indicator_id = %s", (previous["id"],))
                self._upsert_indicator(connection, record, period, now)
        return len(records)

    def list_indicators(self, period: str = "primer_parcial") -> list[dict]:
        """Recuperar las tres variables académicas y el código para un periodo."""
        period = _period(period)
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT student_id AS id_estudiante, nota_parcial, asistencia, tareas_entregadas "
                "FROM indicators WHERE period = %s ORDER BY student_id", (period,)
            ).fetchall()
        return [{ID_COLUMN: row[ID_COLUMN], **{feature: float(row[feature]) for feature in FEATURES}} for row in rows]

    def save_predictions(self, records: list[dict], period: str = "primer_parcial") -> int:
        """Persistir puntuaciones sólo si coinciden con los indicadores vigentes; devolver el total."""
        records = _prediction_records(records)
        period = _period(period)
        now = _utc_now()
        with self._connection() as connection:
            for record in sorted(records, key=lambda row: row[ID_COLUMN]):
                student_id = record[ID_COLUMN]
                self._ensure_student(connection, student_id, now)
                previous = self._locked_indicator(connection, student_id, period)
                if previous is None:
                    indicator_id = int(self._upsert_indicator(connection, record, period, now).lastrowid)
                else:
                    if not self._same_indicators(previous, record):
                        raise ValidationError(
                            f"Los indicadores de {student_id} cambiaron. Recarga los datos y vuelve a calcular."
                        )
                    indicator_id = previous["id"]
                connection.execute(
                    "INSERT INTO predictions(indicator_id, puntuacion_riesgo, alerta, origen_modelo, created_at) "
                    "VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE "
                    "puntuacion_riesgo = VALUES(puntuacion_riesgo), alerta = VALUES(alerta), "
                    "origen_modelo = VALUES(origen_modelo), created_at = VALUES(created_at)",
                    (indicator_id, record["puntuacion_riesgo"], int(record["alerta"]), record["origen_modelo"], now),
                )
        return len(records)

    def list_predictions(self, period: str = "primer_parcial") -> list[dict]:
        """Recuperar indicadores y puntuaciones persistidos, con alerta booleana, por periodo."""
        period = _period(period)
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT i.student_id AS id_estudiante, i.nota_parcial, i.asistencia, i.tareas_entregadas, "
                "p.puntuacion_riesgo, p.alerta, p.origen_modelo FROM predictions p "
                "JOIN indicators i ON i.id = p.indicator_id WHERE i.period = %s ORDER BY i.student_id",
                (period,),
            ).fetchall()
        return [{
            ID_COLUMN: row[ID_COLUMN], **{feature: float(row[feature]) for feature in FEATURES},
            "puntuacion_riesgo": float(row["puntuacion_riesgo"]),
            "alerta": bool(row["alerta"]), "origen_modelo": row["origen_modelo"],
        } for row in rows]
