"""Interfaz local de MESSI. Ejecutar con python -m streamlit run app.py."""

from __future__ import annotations

import csv
import hashlib
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from messi.data import ValidationError, load_csv, load_excel, load_pasted, record_from_counts, validate_records
from messi.database import DatabaseError
from messi.paths import database_path
from messi.model import ModelUnavailable, score_records
from messi.storage import SUPPORT_STATUSES, SUPPORT_TYPES
from messi.sqlite_storage import SQLiteStore

PERIOD = "primer_parcial"


def report_csv(records: list[dict]) -> bytes:
    """Exportar indicadores y puntuación sin solicitudes ni notas del tutor."""
    output = io.StringIO(newline="")
    if records:
        writer = csv.DictWriter(output, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    return output.getvalue().encode("utf-8-sig")


def main() -> None:
    """Preparar la sesión y mostrar las vistas Docente, Tutor y Estudiante."""
    import streamlit as st

    st.set_page_config(page_title="MESSI | Acompañamiento escolar", page_icon="📚", layout="wide")
    st.title("MESSI")
    st.write("Alerta y acompañamiento escolar")
    st.warning("Demostración local con datos sintéticos. El selector de rol no autentica usuarios; usa sólo información ficticia.")
    st.caption("Las alertas orientan la revisión de un tutor. No cambian calificaciones ni aplican sanciones.")
    role = st.sidebar.radio("Vista de demostración", ["Docente", "Tutor", "Estudiante"])
    st.sidebar.caption("Los apoyos funcionan incluso cuando no hay una predicción disponible.")
    store = None
    storage_error = None
    try:
        store = SQLiteStore(database_path())
    except DatabaseError as exc:
        storage_error = exc
    if role == "Docente":
        show_teacher(st, store, storage_error=storage_error)
    else:
        try:
            store = require_store(store, storage_error)
            if role == "Tutor":
                show_tutor(st, store)
            else:
                show_student(st, store)
        except DatabaseError as exc:
            st.error(f"No se pudo acceder a SQLite para consultar los datos y el registro de apoyos: {exc}")


def require_store(store: SQLiteStore | None, error: DatabaseError | None = None) -> SQLiteStore:
    """Obtener SQLite disponible o conservar el mensaje del fallo inicial."""
    if store is None:
        raise error or DatabaseError("No pude abrir la base local. Revisa la carpeta de datos y el diagnóstico.")
    return store


def accept_records(st, records: list[dict], *, origin: str = "capture") -> None:
    """Actualizar los indicadores e invalidar resultados si cambiaron los datos."""
    if records != st.session_state.get("records"):
        st.session_state.pop("predictions", None)
    st.session_state["records"] = records
    st.session_state["records_origin"] = origin


def prepare_form(st, name: str) -> None:
    """Limpiar sólo un envío confirmado, antes de crear sus controles."""
    for key, value in st.session_state.pop(f"reset_{name}", {}).items():
        st.session_state[key] = value
    message = st.session_state.pop(f"success_{name}", None)
    if message:
        st.success(message)


def confirm_form(st, name: str, fields: dict[str, object], message: str) -> None:
    """Programar limpieza y confirmación después de una escritura exitosa."""
    st.session_state[f"reset_{name}"] = fields
    st.session_state[f"success_{name}"] = message
    st.rerun()


def show_indicators(st, records: list[dict]) -> None:
    """Presentar indicadores y alertas con etiquetas comprensibles en español."""
    labels = {"id_estudiante": "Código del estudiante", "nota_parcial": "Nota del primer parcial", "asistencia": "Asistencia (%)", "tareas_entregadas": "Tareas entregadas (%)", "puntuacion_riesgo": "Puntuación de demostración", "alerta": "Revisar con tutor", "origen_modelo": "Origen del modelo"}
    st.dataframe([{labels.get(k, k): v for k, v in row.items()} for row in records], hide_index=True, width="stretch")


def show_teacher(st, store: SQLiteStore | None = None, *, storage_error: DatabaseError | None = None) -> None:
    """Capturar, validar, guardar y puntuar indicadores del primer parcial."""
    st.header("Datos del primer parcial")
    prepare_form(st, "capture")
    st.write("Puedes llenar una plantilla de Excel, escribir los datos aquí o pegar una tabla. Usa notas de 0 a 10 y porcentajes de 0 a 100.")
    st.caption("En esta demostración usa sólo datos ficticios y códigos de estudiante, sin nombres ni información personal.")
    source = st.radio("¿Cómo quieres ingresar los datos?", ["Excel o CSV", "Captura directa", "Pegar tabla", "Ejemplo sintético"], horizontal=True)
    if source != st.session_state.get("input_source"):
        st.session_state["input_source"] = source
        st.session_state.pop("records", None)
        st.session_state.pop("predictions", None)
        st.session_state.pop("records_origin", None)
        st.session_state.pop("uploaded_fingerprint", None)
    try:
        if source == "Excel o CSV":
            template = ROOT / "data" / "synthetic" / "Plantilla_MESSI.xlsx"
            if template.exists():
                st.download_button("Descargar plantilla de Excel", template.read_bytes(), "Plantilla_MESSI.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.write("Reemplaza las filas de ejemplo, guarda el archivo y cárgalo aquí. Escribe 80 para 80 %. Los archivos antiguos .xls deben guardarse como .xlsx.")
            uploaded = st.file_uploader("Seleccionar archivo de Excel o CSV", type=["xlsx", "csv"])
            if uploaded is not None:
                content = uploaded.getvalue()
                fingerprint = hashlib.sha256(content).hexdigest()
                if st.session_state.get("records_origin") != "database" or fingerprint != st.session_state.get("uploaded_fingerprint"):
                    loader = load_excel if uploaded.name.lower().endswith(".xlsx") else load_csv
                    accept_records(st, loader(content))
                st.session_state["uploaded_fingerprint"] = fingerprint
            else:
                st.session_state.pop("uploaded_fingerprint", None)
                if st.session_state.get("records_origin") != "database":
                    st.session_state.pop("records", None)
                    st.session_state.pop("predictions", None)
        elif source == "Captura directa":
            st.write("Agrega un estudiante por vez. Si dejas el código vacío, se asignará uno temporal para esta demostración.")
            use_counts = st.radio("¿Cómo tienes la asistencia y las tareas?", ["Porcentajes", "Cantidades registradas"], horizontal=True) == "Cantidades registradas"
            with st.form("capture_form", clear_on_submit=False):
                student_id = st.text_input("Código del estudiante (opcional)", placeholder="EST-001", max_chars=12, key="capture_id")
                grade = st.number_input("Nota del primer parcial", min_value=0.0, max_value=10.0, value=None, step=0.1, key="capture_grade")
                if use_counts:
                    attendance_count = st.number_input("Sesiones asistidas", min_value=0, value=None, step=1, key="capture_attendance_count")
                    sessions_count = st.number_input("Sesiones impartidas", min_value=0, value=None, step=1, key="capture_sessions_count")
                    homework_count = st.number_input("Tareas entregadas", min_value=0, value=None, step=1, key="capture_homework_count")
                    assigned_count = st.number_input("Tareas solicitadas", min_value=0, value=None, step=1, key="capture_assigned_count")
                else:
                    attendance = st.number_input("Asistencia (%)", min_value=0.0, max_value=100.0, value=None, step=1.0, key="capture_attendance")
                    homework = st.number_input("Tareas entregadas (%)", min_value=0.0, max_value=100.0, value=None, step=1.0, key="capture_homework")
                submitted = st.form_submit_button("Agregar estudiante")
            if submitted:
                current = st.session_state.get("records", [])
                if not student_id.strip():
                    used = {r["id_estudiante"] for r in current}
                    index = 1
                    while f"EST-{index:04d}" in used:
                        index += 1
                    student_id = f"EST-{index:04d}"
                if use_counts:
                    record = record_from_counts(student_id, grade, attendance_count, sessions_count, homework_count, assigned_count)
                else:
                    record = {"id_estudiante": student_id, "nota_parcial": grade, "asistencia": attendance, "tareas_entregadas": homework}
                accept_records(st, validate_records([*current, record]))
                confirm_form(st, "capture", {"capture_id": "", "capture_grade": None, "capture_attendance": None, "capture_homework": None, "capture_attendance_count": None, "capture_sessions_count": None, "capture_homework_count": None, "capture_assigned_count": None}, "Estudiante agregado. Puedes capturar el siguiente.")
        elif source == "Pegar tabla":
            st.write("Copia las filas desde Excel y pégalas aquí. Puedes incluir los encabezados de la plantilla o pegar sólo nota, asistencia y tareas; en ese caso se asignan códigos temporales.")
            st.caption("También puedes separar las columnas con punto y coma: 5,8;70;50. Si incluyes códigos: EST-001;5,8;70;50. Una fila por estudiante.")
            with st.form("paste_form"):
                pasted = st.text_area("Tabla del primer parcial", height=180, max_chars=100000)
                submitted = st.form_submit_button("Revisar tabla pegada")
            if submitted:
                accept_records(st, load_pasted(pasted))
        else:
            if st.button("Cargar ejemplo sintético"):
                sample = ROOT / "data" / "synthetic" / "students_demo.csv"
                accept_records(st, load_csv(sample))
    except (ValidationError, OSError, ImportError) as exc:
        # Un archivo o pegado inválido descarta su conjunto; una fila manual
        # fallida conserva las filas que el docente ya había capturado.
        if source != "Captura directa":
            st.session_state.pop("records", None)
        st.session_state.pop("predictions", None)
        st.error(str(exc))
        if source != "Captura directa":
            return
    if st.button("Cargar indicadores guardados"):
        try:
            saved = require_store(store, storage_error).list_indicators(period=PERIOD)
            if saved:
                accept_records(st, validate_records(saved), origin="database")
                st.session_state.pop("predictions", None)
                st.success(f"Indicadores guardados cargados: {len(saved)} estudiantes.")
            else:
                st.info("Todavía no hay indicadores guardados para el primer parcial.")
        except DatabaseError as exc:
            st.error(f"No se pudieron cargar los indicadores desde SQLite: {exc}")
        except ValidationError as exc:
            st.error(f"Los indicadores guardados no son válidos: {exc}")
    records = st.session_state.get("records", [])
    if not records:
        st.info("Carga un archivo o el ejemplo sintético para revisar los indicadores.")
        return
    st.success(f"Datos válidos: {len(records)} estudiantes.")
    show_indicators(st, records)
    st.caption("Conserva los códigos para identificar cada apoyo. Los códigos automáticos son temporales y no enlazan listas distintas de forma fiable.")
    if st.button("Guardar indicadores"):
        try:
            require_store(store, storage_error).save_indicators(records, period=PERIOD)
        except (DatabaseError, ValueError) as exc:
            st.error(f"No se pudieron guardar los indicadores en SQLite: {exc}")
        else:
            st.success(f"Indicadores guardados para {len(records)} estudiantes.")
    if st.button("Calcular riesgo de demostración"):
        try:
            st.session_state["predictions"] = score_records(records, ROOT / "models" / "messi_demo.joblib")
        except ModelUnavailable as exc:
            st.session_state.pop("predictions", None)
            st.info(str(exc))
        except (ValueError, OSError, ImportError) as exc:
            st.session_state.pop("predictions", None)
            st.error(f"No se pudo calcular la demostración: {exc}")
        else:
            try:
                require_store(store, storage_error).save_predictions(st.session_state["predictions"], period=PERIOD)
            except (DatabaseError, ValueError) as exc:
                st.warning(f"La predicción está disponible en esta sesión, pero no se pudo guardar en SQLite: {exc}")
    predictions = st.session_state.get("predictions")
    if predictions:
        st.subheader("Resultado de demostración")
        st.warning("Modelo entrenado con datos sintéticos. Puntuación de 0 a 1 y umbral de demostración; no validado para estudiantes reales.")
        show_indicators(st, predictions)
        st.caption("Alerta = revisar el caso con un tutor. Los indicadores mostrados son datos observados, no causas ni explicación exacta de la red.")
        st.download_button("Descargar reporte", report_csv(predictions), "reporte_messi_demo.csv", "text/csv")


def show_student(st, store: SQLiteStore) -> None:
    """Registrar una solicitud ficticia independiente de cualquier alerta."""
    st.header("Solicitar apoyo")
    prepare_form(st, "request")
    st.write("Puedes pedir ayuda aunque no tengas una alerta. Para esta demostración, escribe un identificador ficticio y un mensaje ficticio.")
    with st.form("request_form", clear_on_submit=False):
        student_id = st.text_input("Identificador del estudiante", placeholder="EST-001", max_chars=12, key="request_id")
        message = st.text_area("¿En qué necesitas apoyo?", max_chars=1000, key="request_message")
        submitted = st.form_submit_button("Enviar solicitud")
    if submitted:
        try:
            request_id = store.create_request(student_id, message)
        except (ValueError, DatabaseError) as exc:
            st.error(str(exc))
        else:
            confirm_form(st, "request", {"request_id": "", "request_message": ""}, f"Solicitud {request_id} registrada. El tutor podrá revisarla.")


def show_tutor(st, store: SQLiteStore) -> None:
    """Consultar indicadores y solicitudes, acordar apoyos y registrar seguimiento."""
    st.header("Apoyos y seguimiento")
    prepare_form(st, "support")
    prepare_form(st, "followup")
    st.write("Revisa las solicitudes y acuerda el apoyo con el estudiante. Puedes registrarlo sin una alerta de IA.")
    predictions = st.session_state.get("predictions")
    records = st.session_state.get("records")
    if not records and not predictions:
        records = store.list_indicators(period=PERIOD)
        predictions = store.list_predictions(period=PERIOD)
        if records:
            accept_records(st, records, origin="database")
        if predictions:
            st.session_state["predictions"] = predictions
    if predictions:
        st.subheader("Indicadores y alertas de demostración")
        show_indicators(st, predictions)
    elif records:
        st.subheader("Indicadores disponibles")
        show_indicators(st, records)
        st.caption("Predicción pendiente; el registro de apoyos está disponible.")
    st.subheader("Solicitudes recibidas")
    requests = store.list_requests()
    if requests:
        st.dataframe(requests, hide_index=True, width="stretch")
    else:
        st.info("Todavía no hay solicitudes.")
    with st.form("support_form", clear_on_submit=False):
        student_id = st.text_input("Identificador del estudiante", placeholder="EST-001", max_chars=12, key="support_student_id")
        support_type = st.selectbox("Tipo de apoyo", SUPPORT_TYPES)
        notes = st.text_area("Acuerdo de apoyo ficticio", max_chars=1000, key="support_notes")
        submitted = st.form_submit_button("Registrar apoyo")
    if submitted:
        try:
            support_id = store.create_support(student_id, support_type, notes)
        except (ValueError, DatabaseError) as exc:
            st.error(str(exc))
        else:
            confirm_form(st, "support", {"support_student_id": "", "support_notes": ""}, f"Apoyo {support_id} registrado.")
    supports = store.list_supports()
    st.subheader("Apoyos registrados")
    if not supports:
        st.info("Registra un apoyo para agregar su seguimiento.")
        return
    st.dataframe(supports, hide_index=True, width="stretch")
    options = {s["id"]: f'{s["id"]} · {s["student_id"]} · {s["support_type"]}' for s in supports}
    support_id = st.selectbox("Apoyo para seguimiento", list(options), format_func=options.get, key="support_selection")
    current_status = next(s["status"] for s in supports if s["id"] == support_id)
    with st.form("followup_form", clear_on_submit=False):
        status = st.selectbox("Estado del apoyo", SUPPORT_STATUSES, index=SUPPORT_STATUSES.index(current_status), key=f"status_{support_id}_{current_status}")
        notes = st.text_area("Nota ficticia de seguimiento", max_chars=1000, key="followup_notes")
        submitted = st.form_submit_button("Guardar seguimiento")
    if submitted:
        try:
            store.add_followup(support_id, notes, status)
        except (ValueError, DatabaseError) as exc:
            st.error(str(exc))
        else:
            confirm_form(st, "followup", {"followup_notes": ""}, "Seguimiento guardado.")
    st.subheader("Historial del apoyo seleccionado")
    followups = store.list_followups(support_id)
    if followups:
        st.dataframe(followups, hide_index=True, width="stretch")
    else:
        st.caption("Este apoyo aún no tiene seguimiento.")


if __name__ == "__main__":
    main()
