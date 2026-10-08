"""Presentación local de MESSI, sin recursos ni fuentes externas."""

from __future__ import annotations

from datetime import datetime
from html import escape


STYLE = """
<style>
:root { --messi-navy:#122c39; --messi-teal:#167a72; --messi-muted:#526773; }
.stApp { background:#f5f8f7; color:#122c39; font-family:'Segoe UI',sans-serif; }
[data-testid="stHeader"] { background:rgba(245,248,247,.94); }
[data-testid="stMainBlockContainer"] { max-width:1260px; padding:2rem 2.2rem 3rem; }
[data-testid="stSidebar"] { background:#fff; border-right:1px solid #dde8e4; }
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { padding-top:1.7rem; }
h1,h2,h3 { color:#122c39; letter-spacing:-.035em; }
h2 { font-size:1.8rem !important; padding-top:.25rem !important; }
h3 { font-size:1.15rem !important; }
p, label, input, textarea, button { font-family:'Segoe UI',sans-serif !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color:#526773 !important; }
[data-testid="stVerticalBlockBorderWrapper"] > div { border-color:#dce7e3 !important; border-radius:16px !important; background:white; }
[data-testid="stForm"] { border:1px solid #dce7e3; border-radius:16px; padding:1.25rem; background:#fff; }
[data-testid="stButton"] button, [data-testid="stDownloadButton"] button,
[data-testid="stFormSubmitButton"] button { min-height:44px; border-radius:10px; font-weight:600; border-color:#bfd5cc; }
button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] { background:#167a72; border-color:#167a72; color:white; }
button[kind="primary"]:hover { background:#11645e; border-color:#11645e; color:white; }
button:focus-visible, input:focus-visible, textarea:focus-visible,
[role="radio"]:focus-visible, [role="combobox"]:focus-visible { outline:3px solid #a45d13 !important; outline-offset:3px; }
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea { background:#f8fbfa; }
[data-testid="stRadio"] [role="radiogroup"] { gap:.65rem; }
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label { background:#f5f8f7; border:1px solid #dce7e3; border-radius:12px; padding:.7rem; margin:0 0 .35rem; width:100%; }
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) { background:#e6f3ee; border-color:#167a72; }
[data-testid="stMetric"] { background:white; border:1px solid #dce7e3; border-radius:14px; padding:1rem 1.15rem; }
[data-testid="stMetricLabel"] { color:#526773; }
[data-testid="stMetricValue"] { color:#122c39; font-size:1.85rem; }
[data-testid="stAlert"] { border-radius:12px; }
[data-testid="stExpander"] { border-color:#dce7e3; border-radius:12px; background:white; }
.messi-brand { display:flex; align-items:center; gap:12px; margin-bottom:1.5rem; }
.messi-mark { display:grid; place-items:center; width:46px; height:46px; border-radius:14px; background:#167a72; color:white; font-size:25px; font-weight:800; }
.messi-brand strong { display:block; font-size:24px; letter-spacing:.04em; }
.messi-brand small { color:#526773; font-size:12px; }
.messi-hero { display:flex; justify-content:space-between; align-items:center; gap:1rem; padding:1.25rem 1.5rem; border-radius:20px; background:linear-gradient(115deg,#122c39,#1a514f); color:white; margin-bottom:.7rem; }
.messi-hero strong { display:block; font-size:23px; letter-spacing:-.02em; }
.messi-hero p { margin:.25rem 0 0; color:#d6ebe5; font-size:14px; }
.messi-badge { display:inline-block; border:1px solid #bdd8c9; border-radius:100px; padding:6px 11px; background:#e6f3ee; color:#155d55; font-size:12px; font-weight:600; white-space:nowrap; }
.messi-hero .messi-badge { background:#e3f1e9; color:#173f38; }
.messi-steps { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin:.4rem 0 1.4rem; }
.messi-step { padding:13px 15px; border:1px solid #dce7e3; background:#fff; border-radius:13px; }
.messi-step strong { display:block; font-size:14px; margin-bottom:4px; }
.messi-step span { display:block; font-size:12px; color:#526773; }
.messi-step.done { border-color:#75b9a4; background:#edf7f2; }
.messi-step.active { border-color:#167a72; box-shadow:inset 0 3px #167a72; }
.messi-kicker { color:#167a72; font-size:12px; font-weight:700; letter-spacing:.09em; text-transform:uppercase; margin:1.2rem 0 .15rem; }
.messi-empty { padding:1.8rem 1.4rem; border:1px dashed #b9cec3; border-radius:16px; background:#fff; text-align:center; }
.messi-empty strong { display:block; font-size:18px; margin-bottom:8px; }
.messi-empty p { font-size:14px; color:#526773; margin:0; }
.messi-tip { color:#526773; font-size:13px; line-height:1.7; margin-top:1rem; }
.messi-footnote { color:#526773; font-size:12px; margin-top:1.5rem; padding-top:1rem; border-top:1px solid #dce7e3; }
@media(max-width:900px) {
 [data-testid="stMainBlockContainer"] { padding:1rem 1rem 2rem; }
 .messi-hero { padding:1rem; align-items:flex-start; flex-direction:column; }
 .messi-hero strong { font-size:20px; }
 .messi-steps { grid-template-columns:1fr; gap:7px; }
 .messi-step { padding:9px 12px; }
 h2 { font-size:1.5rem !important; }
 [data-testid="stMetric"] { padding:.8rem; }
}
</style>
"""

SUPPORT_LABELS = {"Tutoria": "Tutoría académica", "Apoyo accesible": "Apoyo accesible", "Orientacion": "Orientación"}
TABLE_LABELS = {
    "id": "Folio", "student_id": "Código del estudiante", "message": "Solicitud",
    "created_at": "Fecha (hora local)", "support_type": "Tipo de apoyo",
    "notes": "Nota", "status": "Estado", "support_id": "Folio del apoyo",
}


def support_label(value: str) -> str:
    """Mostrar una etiqueta legible sin cambiar el tipo almacenado."""
    return SUPPORT_LABELS.get(value, value)


def readable_rows(rows: list[dict]) -> list[dict]:
    """Traducir una copia para mostrar; conservar intactos los datos de SQLite."""
    result = []
    for row in rows:
        translated = {}
        for key, value in row.items():
            if key == "created_at" and isinstance(value, str):
                try:
                    # El sistema operativo aplica su zona local, también en el .exe.
                    parsed = datetime.fromisoformat(value)
                    if parsed.tzinfo is not None:
                        value = parsed.astimezone().strftime("%d/%m/%Y · %H:%M")
                except ValueError:
                    pass
            elif key == "support_type":
                value = support_label(value)
            translated[TABLE_LABELS.get(key, key)] = value
        result.append(translated)
    return result


def setup_page(st) -> str:
    """Crear cabecera y navegación de las tres vistas de demostración."""
    st.markdown(STYLE, unsafe_allow_html=True)
    st.sidebar.markdown('<div class="messi-brand"><span class="messi-mark">M</span><div><strong>MESSI</strong><small>Acompañamiento escolar</small></div></div>', unsafe_allow_html=True)
    role = st.sidebar.radio("Vista de demostración", ["Docente", "Tutor", "Estudiante"])
    descriptions = {
        "Docente": "Carga los indicadores, revísalos y genera un reporte.",
        "Tutor": "Revisa solicitudes, acuerda apoyos y da seguimiento.",
        "Estudiante": "Solicita ayuda con o sin una alerta de demostración.",
    }
    st.sidebar.caption(descriptions[role])
    st.sidebar.divider()
    st.sidebar.markdown('<span class="messi-badge">Primer parcial · Demo local</span>', unsafe_allow_html=True)
    with st.sidebar.expander("Acerca de esta demostración"):
        st.caption("Usa sólo información ficticia. El selector de rol no autentica usuarios.")
        st.caption("El modelo utiliza datos sintéticos y no está validado para estudiantes reales.")
        st.caption("Las alertas orientan al tutor; no cambian calificaciones ni aplican sanciones.")
    st.sidebar.caption("Los apoyos funcionan incluso cuando no hay una predicción disponible.")
    st.markdown('<div class="messi-hero"><div><strong>Cada estudiante, un acompañamiento</strong><p>Organiza los indicadores y convierte la revisión en acciones de apoyo.</p></div><span class="messi-badge">MESSI · 0.4.0</span></div>', unsafe_allow_html=True)
    st.caption("Demostración local con datos sintéticos. Usa códigos ficticios, sin nombres ni información personal.")
    return role


def teacher_steps(st, *, loaded: bool, saved: bool, calculated: bool) -> None:
    """Representar el avance confirmado por el estado de la sesión."""
    steps = [
        ("1. Cargar y revisar", "Datos validados" if loaded else "Elige cómo ingresar los datos", "done" if loaded else "active"),
        ("2. Guardar indicadores", "Guardados en la base local" if saved else "Conserva los datos para el tutor", "done" if saved else ("active" if loaded else "")),
        ("3. Calcular y descargar", "Resultado disponible" if calculated else "Genera el reporte de demostración", "done" if calculated else ""),
    ]
    content = "".join(f'<div class="messi-step {state}"><strong>{escape(title)}</strong><span>{escape(text)}</span></div>' for title, text, state in steps)
    st.markdown(f'<div class="messi-steps">{content}</div>', unsafe_allow_html=True)


def empty_state(st, title: str, detail: str) -> None:
    """Explicar el siguiente paso cuando un bloque todavía no contiene datos."""
    st.markdown(f'<div class="messi-empty"><strong>{escape(title)}</strong><p>{escape(detail)}</p></div>', unsafe_allow_html=True)


def kicker(st, text: str) -> None:
    """Identificar la vista activa antes de su título principal."""
    st.markdown(f'<div class="messi-kicker">{escape(text)}</div>', unsafe_allow_html=True)
