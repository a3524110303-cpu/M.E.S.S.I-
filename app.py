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
from messi.presentation import empty_state, kicker, readable_rows, setup_page, support_label, teacher_steps

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
    role = setup_page(st)
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
        st.session_state.pop("saved_fingerprint", None)
        st.session_state.pop("predictions_saved", None)
    st.session_state["records"] = records
    st.session_state["records_origin"] = origin
    if origin == "database":
        st.session_state["saved_fingerprint"] = records_fingerprint(records)


def records_fingerprint(records: list[dict]) -> str:
    """Reconocer el conjunto que se confirmó guardado, sin usar datos personales."""
    return hashlib.sha256(report_csv(records)).hexdigest()


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
    kicker(st, "Vista docente")
    st.header("Datos del primer parcial")
    prepare_form(st, "capture")
    st.write("Carga los indicadores, revisa que sean correctos y compártelos con el tutor.")
    progress = st.empty()
    existing = st.session_state.get("records", [])
    teacher_steps(progress, loaded=bool(existing), saved=bool(existing) and st.session_state.get("saved_fingerprint") == records_fingerprint(existing), calculated=bool(st.session_state.get("predictions")))
    st.subheader("1. Elige cómo ingresar los datos")
    source = st.radio("¿Cómo quieres ingresar los datos?", ["Excel o CSV", "Captura directa", "Pegar tabla", "Ejemplo sintético"], horizontal=True)
    if source != st.session_state.get("input_source"):
        st.session_state["input_source"] = source
        st.session_state.pop("records", None)
        st.session_state.pop("predictions", None)
        st.session_state.pop("records_origin", None)
        st.session_state.pop("uploaded_fingerprint", None)
        st.session_state.pop("saved_fingerprint", None)
        st.session_state.pop("predictions_saved", None)
        teacher_steps(progress, loaded=False, saved=False, calculated=False)
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
                    st.session_state.pop("saved_fingerprint", None)
                    st.session_state.pop("predictions_saved", None)
        elif source == "Captura directa":
            st.write("Agrega un estudiante por vez. Si dejas el código vacío, se asignará uno temporal para esta demostración.")
            use_counts = st.radio("¿Cómo tienes la asistencia y las tareas?", ["Porcentajes", "Cantidades registradas"], horizontal=True) == "Cantidades registradas"
            with st.form("capture_form", clear_on_submit=False):
                left, right = st.columns(2)
                with left:
                    student_id = st.text_input("Código del estudiante (opcional)", placeholder="EST-001", max_chars=12, key="capture_id", help="EST- seguido de 3 a 8 dígitos. Vacío: se asigna un código temporal.")
                with right:
                    grade = st.number_input("Nota del primer parcial", min_value=0.0, max_value=10.0, value=None, step=0.1, key="capture_grade", placeholder="De 0 a 10")
                if use_counts:
                    left, right = st.columns(2)
                    with left:
                        attendance_count = st.number_input("Sesiones asistidas", min_value=0, value=None, step=1, key="capture_attendance_count")
                        sessions_count = st.number_input("Sesiones impartidas", min_value=0, value=None, step=1, key="capture_sessions_count")
                    with right:
                        homework_count = st.number_input("Tareas entregadas", min_value=0, value=None, step=1, key="capture_homework_count")
                        assigned_count = st.number_input("Tareas solicitadas", min_value=0, value=None, step=1, key="capture_assigned_count")
                else:
                    left, right = st.columns(2)
                    with left:
                        attendance = st.number_input("Asistencia (%)", min_value=0.0, max_value=100.0, value=None, step=1.0, key="capture_attendance", placeholder="Ejemplo: 80")
                    with right:
                        homework = st.number_input("Tareas entregadas (%)", min_value=0.0, max_value=100.0, value=None, step=1.0, key="capture_homework", placeholder="Ejemplo: 75")
                st.caption("Completa todos los indicadores. El código es el único campo opcional.")
                submitted = st.form_submit_button("Agregar estudiante", type="primary")
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
                submitted = st.form_submit_button("Revisar tabla pegada", type="primary")
            if submitted:
                accept_records(st, load_pasted(pasted))
        else:
            with st.container(border=True):
                st.write("**Explora MESSI con 8 estudiantes ficticios**")
                st.caption("Un recorrido rápido para conocer las tablas y el reporte, sin preparar un archivo.")
                load_sample = st.button("Cargar ejemplo sintético", type="primary")
            if load_sample:
                sample = ROOT / "data" / "synthetic" / "students_demo.csv"
                accept_records(st, load_csv(sample))
    except (ValidationError, OSError, ImportError) as exc:
        # Un archivo o pegado inválido descarta su conjunto; una fila manual
        # fallida conserva las filas que el docente ya había capturado.
        if source != "Captura directa":
            st.session_state.pop("records", None)
            st.session_state.pop("saved_fingerprint", None)
        st.session_state.pop("predictions", None)
        st.session_state.pop("predictions_saved", None)
        st.error(f"Revisa los datos antes de continuar. {exc}")
        if source != "Captura directa":
            teacher_steps(progress, loaded=False, saved=False, calculated=False)
            return
    st.caption("¿Quieres continuar un registro anterior? Puedes recuperar los indicadores de la base local.")
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
        teacher_steps(progress, loaded=False, saved=False, calculated=False)
        empty_state(st, "Tu lista aparecerá aquí", "Carga un archivo o el ejemplo sintético para revisar los indicadores.")
        return
    st.subheader("2. Revisa y guarda los indicadores")
    metrics = st.columns(3)
    metrics[0].metric("Estudiantes en la lista", len(records))
    metrics[1].metric("Nota promedio", f"{sum(r['nota_parcial'] for r in records) / len(records):.1f} / 10")
    metrics[2].metric("Asistencia promedio", f"{sum(r['asistencia'] for r in records) / len(records):.0f} %")
    with st.container(border=True):
        st.success(f"Datos válidos: {len(records)} estudiantes.")
        show_indicators(st, records)
        st.caption("Conserva los códigos para identificar cada apoyo. Los códigos automáticos son temporales y no enlazan listas distintas de forma fiable.")
    save_clicked = st.button("Guardar indicadores", width="stretch")
    if save_clicked:
        try:
            require_store(store, storage_error).save_indicators(records, period=PERIOD)
        except (DatabaseError, ValueError) as exc:
            st.error(f"No se pudieron guardar los indicadores en SQLite: {exc}")
        else:
            st.session_state["saved_fingerprint"] = records_fingerprint(records)
            st.success(f"Indicadores guardados para {len(records)} estudiantes.")
    saved = st.session_state.get("saved_fingerprint") == records_fingerprint(records)
    st.caption("Guardados en la base local: el tutor puede consultarlos." if saved else "Estos indicadores están en esta sesión. Guárdalos para que el tutor pueda consultarlos.")
    st.subheader("3. Genera el reporte de demostración")
    st.caption("El cálculo intenta guardar indicadores y resultados en la base local. Si cambiaste datos ya guardados, guarda primero los indicadores nuevos.")
    if st.button("Calcular riesgo de demostración", type="primary", width="stretch"):
        st.session_state.pop("predictions_saved", None)
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
            else:
                st.session_state["saved_fingerprint"] = records_fingerprint(records)
                st.session_state["predictions_saved"] = True
    predictions = st.session_state.get("predictions")
    teacher_steps(progress, loaded=True, saved=st.session_state.get("saved_fingerprint") == records_fingerprint(records), calculated=bool(predictions))
    if predictions:
        st.subheader("Resultado de demostración")
        review_count = sum(bool(row["alerta"]) for row in predictions)
        summary = st.columns(2)
        summary[0].metric("Casos para revisar con tutor", review_count)
        summary[1].metric("Resultados calculados", len(predictions))
        st.warning("Modelo entrenado con datos sintéticos. Puntuación de 0 a 1 y umbral de demostración; no validado para estudiantes reales.")
        show_indicators(st, predictions)
        st.caption("Alerta = revisar el caso con un tutor. Los indicadores mostrados son datos observados, no causas ni explicación exacta de la red.")
        st.caption("Resultados guardados en la base local." if st.session_state.get("predictions_saved") else "Resultado disponible en esta sesión. Descarga el reporte para conservar una copia.")
        st.download_button("Descargar reporte", report_csv(predictions), "reporte_messi_demo.csv", "text/csv", type="primary")


def show_student(st, store: SQLiteStore) -> None:
    """Registrar una solicitud ficticia independiente de cualquier alerta."""
    kicker(st, "Vista estudiante")
    st.header("Solicitar apoyo")
    prepare_form(st, "request")
    st.write("Pedir ayuda es el primer paso. Puedes hacerlo aunque no tengas una alerta.")
    form_column, guide_column = st.columns([1.6, 1], gap="large")
    with form_column:
        with st.form("request_form", clear_on_submit=False):
            st.subheader("Cuéntale al tutor qué necesitas")
            student_id = st.text_input("Identificador del estudiante", placeholder="EST-001", max_chars=12, key="request_id", help="Usa el mismo código ficticio de la lista del docente: EST- y de 3 a 8 dígitos.")
            message = st.text_area("¿En qué necesitas apoyo?", placeholder="Ejemplo ficticio: necesito organizar mis tareas para el siguiente parcial.", height=160, max_chars=1000, key="request_message")
            st.caption("Usa un código y un mensaje ficticios. Evita nombres y datos personales.")
            submitted = st.form_submit_button("Enviar solicitud", type="primary", width="stretch")
    with guide_column:
        with st.container(border=True):
            st.subheader("¿Qué ocurre después?")
            st.write("**1. Tu solicitud se registra**\n\nAl enviarla, recibirás un folio de confirmación.")
            st.write("**2. El tutor la revisa**\n\nPodrá verla en la bandeja de solicitudes.")
            st.write("**3. Acuerdan un apoyo**\n\nEl tutor registra el acuerdo y su seguimiento.")
            st.caption("Esta demostración local no envía notificaciones. El tutor debe abrir su vista para consultar las solicitudes.")
    if submitted:
        try:
            request_id = store.create_request(student_id, message)
        except (ValueError, DatabaseError) as exc:
            st.error(str(exc))
        else:
            confirm_form(st, "request", {"request_id": "", "request_message": ""}, f"Solicitud {request_id} registrada. El tutor podrá revisarla.")


def show_tutor(st, store: SQLiteStore) -> None:
    """Consultar indicadores y solicitudes, acordar apoyos y registrar seguimiento."""
    kicker(st, "Vista tutor")
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
            st.session_state["predictions_saved"] = True
    requests = store.list_requests()
    supports = store.list_supports()
    overview = st.columns(3)
    overview[0].metric("Solicitudes recibidas", len(requests))
    overview[1].metric("Apoyos activos", sum(s["status"] != "Cerrado" for s in supports))
    overview[2].metric("Casos para revisar", sum(bool(p["alerta"]) for p in predictions or []))
    st.caption("Solicitudes: total registrado. Apoyos activos: pendientes o en seguimiento. Casos: alertas del conjunto de indicadores visible.")
    if predictions:
        with st.expander("Indicadores y alertas de demostración"):
            st.caption("Puntuaciones sintéticas para orientar una revisión; no cambian calificaciones ni aplican sanciones.")
            show_indicators(st, predictions)
    elif records:
        with st.expander("Indicadores disponibles"):
            show_indicators(st, records)
            st.caption("Predicción pendiente; el registro de apoyos está disponible.")
    else:
        st.caption("Aún no hay indicadores. Puedes atender solicitudes y registrar apoyos desde ahora.")
    inbox_column, agreement_column = st.columns([1.25, 1], gap="large")
    with inbox_column:
        st.subheader("Solicitudes recibidas")
        if requests:
            with st.expander("Ver todas las solicitudes"):
                st.dataframe(readable_rows(requests), hide_index=True, width="stretch")
            request_options = {r["id"]: f'Solicitud {r["id"]} · {r["student_id"]}' for r in requests}
            selected_request_id = st.selectbox("Leer una solicitud", list(request_options), format_func=request_options.get, key="request_selection")
            selected_request = next(r for r in requests if r["id"] == selected_request_id)
            st.caption(f"{selected_request['student_id']} · {readable_rows([selected_request])[0]['Fecha (hora local)']}")
            st.text_area("Detalle de la solicitud", value=selected_request["message"], height=140, disabled=True, key=f"read_request_{selected_request_id}")
            if st.button("Usar este código en el acuerdo", width="stretch"):
                # La asignación ocurre antes de crear el control del formulario.
                st.session_state["support_student_id"] = selected_request["student_id"]
            st.caption("Lee el mensaje y utiliza su código para preparar el acuerdo de apoyo.")
        else:
            empty_state(st, "La bandeja está vacía", "Las solicitudes enviadas desde la vista Estudiante aparecerán aquí.")
    with agreement_column:
        with st.form("support_form", clear_on_submit=False):
            st.subheader("Registrar un acuerdo de apoyo")
            student_id = st.text_input("Identificador del estudiante", placeholder="EST-001", max_chars=12, key="support_student_id")
            support_type = st.selectbox("Tipo de apoyo", SUPPORT_TYPES, format_func=support_label, key="support_type")
            notes = st.text_area("Acuerdo de apoyo ficticio", placeholder="Ejemplo: revisar tareas pendientes el viernes y acordar un plan.", max_chars=1000, key="support_notes")
            submitted = st.form_submit_button("Registrar apoyo", type="primary", width="stretch")
    if submitted:
        try:
            support_id = store.create_support(student_id, support_type, notes)
        except (ValueError, DatabaseError) as exc:
            st.error(str(exc))
        else:
            confirm_form(st, "support", {"support_student_id": "", "support_notes": ""}, f"Apoyo {support_id} registrado.")
    st.divider()
    st.subheader("Apoyos registrados")
    if not supports:
        empty_state(st, "Comienza con un acuerdo", "Registra un apoyo para agregar su seguimiento.")
        return
    st.dataframe(readable_rows(supports), hide_index=True, width="stretch")
    st.subheader("Dar seguimiento a un apoyo")
    options = {s["id"]: f'Apoyo {s["id"]} · {s["student_id"]} · {support_label(s["support_type"])} · {s["status"]}' for s in supports}
    support_id = st.selectbox("Apoyo para seguimiento", list(options), format_func=options.get, key="support_selection")
    current_status = next(s["status"] for s in supports if s["id"] == support_id)
    followup_column, history_column = st.columns([1, 1.25], gap="large")
    with followup_column:
        with st.form("followup_form", clear_on_submit=False):
            status = st.selectbox("Estado del apoyo", SUPPORT_STATUSES, index=SUPPORT_STATUSES.index(current_status), key=f"status_{support_id}_{current_status}")
            notes = st.text_area("Nota ficticia de seguimiento", placeholder="¿Qué se revisó y cuál es el siguiente paso?", max_chars=1000, key="followup_notes")
            submitted = st.form_submit_button("Guardar seguimiento", type="primary", width="stretch")
    if submitted:
        try:
            store.add_followup(support_id, notes, status)
        except (ValueError, DatabaseError) as exc:
            st.error(str(exc))
        else:
            confirm_form(st, "followup", {"followup_notes": ""}, "Seguimiento guardado.")
    with history_column:
        st.subheader("Historial del apoyo seleccionado")
        followups = store.list_followups(support_id)
        if followups:
            st.dataframe(readable_rows(followups), hide_index=True, width="stretch")
        else:
            empty_state(st, "Aquí verás los avances", "Este apoyo aún no tiene seguimiento. Registra la primera nota para comenzar.")


if __name__ == "__main__":
    main()
