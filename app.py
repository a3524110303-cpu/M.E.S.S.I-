"""Interfaz local de MESSI. Ejecutar con python -m streamlit run app.py."""

from __future__ import annotations

import csv
import io
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from messi.data import ValidationError, load_csv, load_excel, load_pasted, record_from_counts, validate_records
from messi.model import ModelUnavailable, score_records
from messi.storage import SUPPORT_STATUSES, SUPPORT_TYPES, SupportStore


def report_csv(records: list[dict]) -> bytes:
    """Exportar indicadores y puntuación sin solicitudes ni notas del tutor."""
    output = io.StringIO(newline="")
    if records:
        writer = csv.DictWriter(output, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    return output.getvalue().encode("utf-8-sig")


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="MESSI | Acompañamiento escolar", page_icon="📚", layout="wide")
    st.title("MESSI")
    st.write("Alerta y acompañamiento escolar")
    st.warning("Demostración local con datos sintéticos. El selector de rol no autentica usuarios; usa sólo información ficticia.")
    st.caption("Las alertas orientan la revisión de un tutor. No cambian calificaciones ni aplican sanciones.")
    role = st.sidebar.radio("Vista de demostración", ["Docente", "Tutor", "Estudiante"])
    st.sidebar.caption("Los apoyos funcionan incluso cuando no hay una predicción disponible.")
    if role == "Docente":
        show_teacher(st)
    else:
        try:
            store = SupportStore(ROOT / "data" / "private" / "messi.sqlite3")
            if role == "Tutor":
                show_tutor(st, store)
            else:
                show_student(st, store)
        except (OSError, sqlite3.Error):
            st.error("No se pudo acceder al registro de apoyos. Cierra otras ejecuciones y vuelve a intentar; los datos del docente siguen disponibles.")


def accept_records(st, records: list[dict]) -> None:
    if records != st.session_state.get("records"):
        st.session_state.pop("predictions", None)
    st.session_state["records"] = records


def show_indicators(st, records: list[dict]) -> None:
    labels = {"id_estudiante": "Código del estudiante", "nota_parcial": "Nota del primer parcial", "asistencia": "Asistencia (%)", "tareas_entregadas": "Tareas entregadas (%)", "puntuacion_riesgo": "Puntuación de demostración", "alerta": "Revisar con tutor", "origen_modelo": "Origen del modelo"}
    st.dataframe([{labels.get(k, k): v for k, v in row.items()} for row in records], hide_index=True, use_container_width=True)


def show_teacher(st) -> None:
    st.header("Datos del primer parcial")
    st.write("Puedes llenar una plantilla de Excel, escribir los datos aquí o pegar una tabla. Usa notas de 0 a 10 y porcentajes de 0 a 100.")
    st.caption("En esta demostración usa sólo datos ficticios y códigos de estudiante, sin nombres ni información personal.")
    source = st.radio("¿Cómo quieres ingresar los datos?", ["Excel o CSV", "Captura directa", "Pegar tabla", "Ejemplo sintético"], horizontal=True)
    if source != st.session_state.get("input_source"):
        st.session_state["input_source"] = source
        st.session_state.pop("records", None)
        st.session_state.pop("predictions", None)
    try:
        if source == "Excel o CSV":
            template = ROOT / "data" / "synthetic" / "Plantilla_MESSI.xlsx"
            if template.exists():
                st.download_button("Descargar plantilla de Excel", template.read_bytes(), "Plantilla_MESSI.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.write("Reemplaza las filas de ejemplo, guarda el archivo y cárgalo aquí. Escribe 80 para 80 %. Los archivos antiguos .xls deben guardarse como .xlsx.")
            uploaded = st.file_uploader("Seleccionar archivo de Excel o CSV", type=["xlsx", "csv"])
            if uploaded is not None:
                loader = load_excel if uploaded.name.lower().endswith(".xlsx") else load_csv
                accept_records(st, loader(uploaded.getvalue()))
            else:
                st.session_state.pop("records", None)
                st.session_state.pop("predictions", None)
        elif source == "Captura directa":
            st.write("Agrega un estudiante por vez. Si dejas el código vacío, se asignará uno temporal para esta demostración.")
            use_counts = st.radio("¿Cómo tienes la asistencia y las tareas?", ["Porcentajes", "Cantidades registradas"], horizontal=True) == "Cantidades registradas"
            with st.form("capture_form", clear_on_submit=True):
                student_id = st.text_input("Código del estudiante (opcional)", placeholder="EST-001", max_chars=12)
                grade = st.number_input("Nota del primer parcial", min_value=0.0, max_value=10.0, value=None, step=0.1)
                if use_counts:
                    attendance_count = st.number_input("Sesiones asistidas", min_value=0, value=None, step=1)
                    sessions_count = st.number_input("Sesiones impartidas", min_value=0, value=None, step=1)
                    homework_count = st.number_input("Tareas entregadas", min_value=0, value=None, step=1)
                    assigned_count = st.number_input("Tareas solicitadas", min_value=0, value=None, step=1)
                else:
                    attendance = st.number_input("Asistencia (%)", min_value=0.0, max_value=100.0, value=None, step=1.0)
                    homework = st.number_input("Tareas entregadas (%)", min_value=0.0, max_value=100.0, value=None, step=1.0)
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
    records = st.session_state.get("records", [])
    if not records:
        st.info("Carga un archivo o el ejemplo sintético para revisar los indicadores.")
        return
    st.success(f"Datos válidos: {len(records)} estudiantes.")
    show_indicators(st, records)
    st.caption("Conserva los códigos para identificar cada apoyo. Los códigos automáticos son temporales y no enlazan listas distintas de forma fiable.")
    if st.button("Calcular riesgo de demostración"):
        try:
            st.session_state["predictions"] = score_records(records, ROOT / "models" / "messi_demo.joblib")
        except ModelUnavailable as exc:
            st.session_state.pop("predictions", None)
            st.info(str(exc))
        except (ValueError, OSError, ImportError) as exc:
            st.session_state.pop("predictions", None)
            st.error(f"No se pudo calcular la demostración: {exc}")
    predictions = st.session_state.get("predictions")
    if predictions:
        st.subheader("Resultado de demostración")
        st.warning("Modelo entrenado con datos sintéticos. Puntuación de 0 a 1 y umbral de demostración; no validado para estudiantes reales.")
        show_indicators(st, predictions)
        st.caption("Alerta = revisar el caso con un tutor. Los indicadores mostrados son datos observados, no causas ni explicación exacta de la red.")
        st.download_button("Descargar reporte", report_csv(predictions), "reporte_messi_demo.csv", "text/csv")


def show_student(st, store: SupportStore) -> None:
    st.header("Solicitar apoyo")
    st.write("Puedes pedir ayuda aunque no tengas una alerta. Para esta demostración, escribe un identificador ficticio y un mensaje ficticio.")
    with st.form("request_form", clear_on_submit=True):
        student_id = st.text_input("Identificador del estudiante", placeholder="EST-001", max_chars=12)
        message = st.text_area("¿En qué necesitas apoyo?", max_chars=1000)
        submitted = st.form_submit_button("Enviar solicitud")
    if submitted:
        try:
            request_id = store.create_request(student_id, message)
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.success(f"Solicitud {request_id} registrada. El tutor podrá revisarla.")


def show_tutor(st, store: SupportStore) -> None:
    st.header("Apoyos y seguimiento")
    st.write("Revisa las solicitudes y acuerda el apoyo con el estudiante. Puedes registrarlo sin una alerta de IA.")
    predictions = st.session_state.get("predictions")
    records = st.session_state.get("records")
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
        st.dataframe(requests, hide_index=True, use_container_width=True)
    else:
        st.info("Todavía no hay solicitudes.")
    with st.form("support_form", clear_on_submit=True):
        student_id = st.text_input("Identificador del estudiante", placeholder="EST-001", max_chars=12)
        support_type = st.selectbox("Tipo de apoyo", SUPPORT_TYPES)
        notes = st.text_area("Acuerdo de apoyo ficticio", max_chars=1000)
        submitted = st.form_submit_button("Registrar apoyo")
    if submitted:
        try:
            support_id = store.create_support(student_id, support_type, notes)
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.success(f"Apoyo {support_id} registrado.")
    supports = store.list_supports()
    st.subheader("Apoyos registrados")
    if not supports:
        st.info("Registra un apoyo para agregar su seguimiento.")
        return
    st.dataframe(supports, hide_index=True, use_container_width=True)
    options = {s["id"]: f'{s["id"]} · {s["student_id"]} · {s["support_type"]}' for s in supports}
    support_id = st.selectbox("Apoyo para seguimiento", list(options), format_func=options.get, key="support_selection")
    current_status = next(s["status"] for s in supports if s["id"] == support_id)
    with st.form("followup_form", clear_on_submit=True):
        status = st.selectbox("Estado del apoyo", SUPPORT_STATUSES, index=SUPPORT_STATUSES.index(current_status), key=f"status_{support_id}_{current_status}")
        notes = st.text_area("Nota ficticia de seguimiento", max_chars=1000)
        submitted = st.form_submit_button("Guardar seguimiento")
    if submitted:
        try:
            store.add_followup(support_id, notes, status)
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.success("Seguimiento guardado.")
            st.rerun()
    st.subheader("Historial del apoyo seleccionado")
    followups = store.list_followups(support_id)
    if followups:
        st.dataframe(followups, hide_index=True, use_container_width=True)
    else:
        st.caption("Este apoyo aún no tiene seguimiento.")


if __name__ == "__main__":
    main()
