"""Presentación estática; nunca guarda datos escolares globalmente."""


def style(st):
    st.markdown(
        """<style>
        :root{--messi-green:#1b6751}
        .stApp{background:#f6f7f3}
        [data-testid="stSidebar"]{background:#183d33;color:#f1f7f3}
        [data-testid="stSidebar"] h1,[data-testid="stSidebar"] p,[data-testid="stSidebar"] label{color:#f1f7f3}
        [data-testid="stMetric"]{background:#fff;border:1px solid #e1e8df;border-radius:14px;padding:19px}
        [data-testid="stMetricLabel"]{color:#627469}
        [data-testid="stForm"]{background:#fff;border:1px solid #dce5d9;border-radius:13px;padding:22px}
        h1,h2,h3{color:#203d30;letter-spacing:-.5px}
        .messi-eyebrow{color:#1b6751;font-size:11px;font-weight:700;letter-spacing:1.8px;margin:18px 0 8px}
        .messi-banner{border:1px solid #dce7d9;border-radius:14px;background:#eaf2e6;padding:22px 26px;margin:16px 0 24px;color:#294833}
        .messi-banner strong{font-size:20px;font-weight:600}
        .messi-banner p{font-size:13px;color:#59705e;margin:9px 0 0}
        .block-container{padding-top:2.1rem;padding-bottom:3rem;max-width:1400px}
        @media(max-width:700px){.block-container{padding:1.3rem 1rem}.messi-banner{padding:18px}}
        </style>""",
        unsafe_allow_html=True,
    )


def header(st, label, title, description):
    # These strings are supplied only by the application's fixed role screens.
    st.markdown(f'<div class="messi-eyebrow">{label}</div>', unsafe_allow_html=True)
    st.title(title)
    st.caption(description)


def model_note(st):
    st.info(
        "Red neuronal demostrativa, entrenada con datos sintéticos del primer parcial. "
        "La puntuación es una señal del modelo, no una probabilidad validada ni un diagnóstico. "
        "La decisión de apoyo corresponde al equipo escolar."
    )


def date_label(value):
    from django.utils import timezone
    return timezone.localtime(value).strftime("%d/%m/%Y %H:%M")


def person(user):
    return user.get_full_name() or user.username


def error(st, exc):
    from django.core.exceptions import PermissionDenied, ValidationError
    from messi.data import ValidationError as DataError
    from messi.model import ModelUnavailable

    if isinstance(exc, ModelUnavailable):
        st.error("El modelo demostrativo no está disponible. El administrador debe revisar su instalación. Las solicitudes y el seguimiento siguen disponibles.")
    elif isinstance(exc, PermissionDenied):
        st.error("Esta acción no está permitida para tu cuenta o tus asignaciones actuales. Actualiza tu espacio y revisa la selección.")
    elif isinstance(exc, ValidationError):
        for message in exc.messages:
            st.error(message)
    elif isinstance(exc, DataError):
        st.error(str(exc))
    else:
        st.error("No pudimos completar la operación. Intenta nuevamente; si el problema continúa, contacta al administrador de tu institución.")
