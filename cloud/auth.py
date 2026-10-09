"""Credenciales Django, bloqueo compartido y sesión privada de Streamlit."""
import math
import time
import unicodedata
from datetime import datetime, timedelta, timezone

SESSION_SECONDS = 8 * 60 * 60
USER_KEY = "_messi_auth_user_id"
HASH_KEY = "_messi_auth_hash"
STARTED_KEY = "_messi_auth_started"
ROLE_KEY = "_messi_auth_role"


def logout(st):
    """Elimina también formularios y resultados del usuario anterior."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def get_session_user(st, now=None):
    from django.contrib.auth import get_user_model
    from django.utils.crypto import constant_time_compare
    from portal.services import role_for
    state = st.session_state
    if USER_KEY not in state:
        return None
    try:
        timestamp = float(time.time() if now is None else now)
        started = float(state[STARTED_KEY])
        if not math.isfinite(started) or not math.isfinite(timestamp) or not 0 <= timestamp - started < SESSION_SECONDS:
            raise ValueError
        user = get_user_model().objects.filter(pk=state[USER_KEY], is_active=True).first()
        role = role_for(user) if user else None
        if user is None or role not in {"admin", "docente", "estudiante", "tutor"} or role != state.get(ROLE_KEY):
            raise ValueError
        if not constant_time_compare(user.get_session_auth_hash(), str(state[HASH_KEY])):
            raise ValueError
    except (KeyError, TypeError, ValueError, OverflowError):
        logout(st)
        return None
    return user


def authenticate_credentials(username, password, now=None):
    """Retorna usuario o None y segundos de bloqueo, sin guardar contraseñas.

    Streamlit documenta que su IP puede falsificarse; el límite se aplica a la
    cuenta normalizada sin confiar en encabezados enviados por el visitante.
    """
    from django.conf import settings
    from django.contrib.auth import authenticate
    from django.db import transaction
    from django.utils.crypto import salted_hmac
    from portal.models import LoginAttempt
    from portal.services import role_for
    raw_username = username if isinstance(username, str) else ""
    normalized = unicodedata.normalize("NFKC", raw_username[:150]).casefold().strip()
    key = salted_hmac("messi.cloud.account", normalized).hexdigest()
    timestamp = float(time.time() if now is None else now)
    current = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    with transaction.atomic():
        LoginAttempt.objects.get_or_create(key=key)
        attempt = LoginAttempt.objects.select_for_update().get(key=key)
        if attempt.blocked_until and attempt.blocked_until > current:
            return None, max(1, math.ceil((attempt.blocked_until - current).total_seconds()))
        if current - attempt.window_started >= timedelta(seconds=settings.MESSI_LOGIN_WINDOW_SECONDS):
            attempt.failures = 0
            attempt.window_started = current
            attempt.blocked_until = None
        user = None
        if normalized and len(raw_username) <= 150 and isinstance(password, str) and 0 < len(password) <= 1024:
            user = authenticate(username=unicodedata.normalize("NFKC", raw_username).strip(), password=password)
        if user is not None and role_for(user) in {"admin", "docente", "estudiante", "tutor"}:
            attempt.failures = 0
            attempt.blocked_until = None
            attempt.window_started = current
            attempt.save(update_fields=["failures", "blocked_until", "window_started"])
            return user, 0
        attempt.failures += 1
        if attempt.failures >= settings.MESSI_LOGIN_MAX_ATTEMPTS:
            attempt.blocked_until = current + timedelta(seconds=settings.MESSI_LOGIN_BLOCK_SECONDS)
        attempt.save(update_fields=["failures", "blocked_until", "window_started"])
        return None, 0


def _submit_login(st):
    username = st.session_state.get("_messi_login_username", "")
    password = st.session_state.get("_messi_login_password", "")
    # Callback antes de crear widgets: vaciar el campo no infringe las reglas
    # de Streamlit y la contraseña no queda guardada después de enviarla.
    st.session_state["_messi_login_password"] = ""
    try:
        user, retry_after = authenticate_credentials(username, password)
        if retry_after:
            st.session_state["_messi_auth_error"] = "Demasiados intentos. Espera unos minutos y vuelve a intentarlo."
        elif user is None:
            st.session_state["_messi_auth_error"] = "Usuario o contraseña incorrectos, o cuenta sin acceso."
        else:
            from portal.services import role_for
            logout(st)
            st.session_state.update({USER_KEY: user.pk, HASH_KEY: user.get_session_auth_hash(),
                                     STARTED_KEY: time.time(), ROLE_KEY: role_for(user)})
    except Exception:
        st.session_state["_messi_auth_error"] = "No se pudo iniciar sesión. Pide al administrador que revise la conexión."
    finally:
        password = None


def login(st):
    try:
        user = get_session_user(st)
    except Exception:
        logout(st)
        st.error("No se pudo comprobar la sesión. Inténtalo de nuevo cuando el servicio esté disponible.")
        return None
    if user is not None:
        return user
    st.subheader("Iniciar sesión")
    st.caption("Entra con la cuenta que te asignó tu escuela.")
    with st.form("messi_cloud_login", clear_on_submit=True):
        st.text_input("Usuario", key="_messi_login_username", max_chars=150)
        st.text_input("Contraseña", type="password", key="_messi_login_password", max_chars=1024)
        st.form_submit_button("Entrar", on_click=_submit_login, args=(st,), width="stretch")
    error = st.session_state.pop("_messi_auth_error", None)
    if error:
        st.error(error)
    return None
