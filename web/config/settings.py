"""Ajustes explícitos del portal: MySQL y HTTPS por defecto.

web/.env es independiente de .env del prototipo. El entorno del proceso
siempre tiene prioridad. SQLite requiere un indicador deliberado de pruebas.
"""

import os
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

WEB_DIR = Path(__file__).resolve().parents[1]
BASE_DIR = WEB_DIR.parent
load_dotenv(WEB_DIR / ".env", override=False)


def env_list(name):
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


def required(name):
    value = os.environ.get(name, "").strip()
    if not value or value.startswith("CAMBIAR_"):
        raise ImproperlyConfigured(f"Configura {name} en web/.env o en el entorno del servidor.")
    return value


def positive_int(name, default):
    try:
        value = int(os.environ.get(name, str(default)))
        if value < 1:
            raise ValueError
    except ValueError as exc:
        raise ImproperlyConfigured(f"{name} debe ser un entero positivo.") from exc
    return value


ENVIRONMENT = os.environ.get("MESSI_WEB_ENV", "production").strip().lower()
if ENVIRONMENT not in {"development", "production"}:
    raise ImproperlyConfigured("MESSI_WEB_ENV sólo admite development o production.")
PRODUCTION = ENVIRONMENT == "production"
DEBUG = not PRODUCTION
TEST_SQLITE = os.environ.get("MESSI_WEB_TEST_SQLITE") == "1"
if PRODUCTION and TEST_SQLITE:
    raise ImproperlyConfigured("SQLite sólo está habilitado para pruebas explícitas en development.")

SECRET_KEY = os.environ.get("MESSI_WEB_SECRET_KEY", "").strip()
if PRODUCTION:
    SECRET_KEY = required("MESSI_WEB_SECRET_KEY")
    if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith("django-insecure-"):
        raise ImproperlyConfigured("MESSI_WEB_SECRET_KEY debe ser una clave aleatoria de al menos 50 caracteres.")
elif not SECRET_KEY or SECRET_KEY.startswith("CAMBIAR_"):
    SECRET_KEY = "django-insecure-messi-development-only-never-deploy-this-key"

ALLOWED_HOSTS = env_list("MESSI_WEB_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env_list("MESSI_WEB_CSRF_TRUSTED_ORIGINS")
if PRODUCTION:
    if not ALLOWED_HOSTS or any("*" in host or host.startswith(".") or "://" in host for host in ALLOWED_HOSTS):
        raise ImproperlyConfigured("Producción requiere MESSI_WEB_ALLOWED_HOSTS con nombres explícitos, sin comodines ni URL.")
    if not CSRF_TRUSTED_ORIGINS:
        raise ImproperlyConfigured("Producción requiere MESSI_WEB_CSRF_TRUSTED_ORIGINS con el origen HTTPS público.")
    for origin in CSRF_TRUSTED_ORIGINS:
        parsed = urlparse(origin)
        if parsed.scheme != "https" or not parsed.hostname or "*" in origin or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ImproperlyConfigured("Cada origen CSRF debe ser una URL HTTPS exacta, sin ruta ni comodines.")
else:
    ALLOWED_HOSTS = ALLOWED_HOSTS or ["localhost", "127.0.0.1", "[::1]"]

INSTALLED_APPS = [
    "portal.admin_config.PortalAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "portal",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [WEB_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

if TEST_SQLITE:
    sqlite_path = os.environ.get("MESSI_WEB_SQLITE_PATH", str(BASE_DIR / ".qa" / "messi-web.sqlite3"))
    if sqlite_path != ":memory:":
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": sqlite_path}}
else:
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": required("MESSI_WEB_DB_NAME"),
        "USER": required("MESSI_WEB_DB_USER"),
        "PASSWORD": required("MESSI_WEB_DB_PASSWORD"),
        "HOST": required("MESSI_WEB_DB_HOST"),
        "PORT": positive_int("MESSI_WEB_DB_PORT", 3306),
        "CONN_MAX_AGE": 60 if PRODUCTION else 0,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            "isolation_level": "read committed",
            "connect_timeout": 10,
        },
    }}
    # Las conexiones a proveedores externos verifican tanto la CA como el
    # nombre del servidor. La red privada de Docker puede seguir sin TLS.
    ssl_ca = os.environ.get("MESSI_WEB_DB_SSL_CA", "").strip()
    verify_tls = os.environ.get("MESSI_WEB_DB_SSL_VERIFY") == "1"
    if verify_tls and not ssl_ca:
        raise ImproperlyConfigured("La verificación TLS de MySQL requiere MESSI_WEB_DB_SSL_CA.")
    if ssl_ca:
        if not Path(ssl_ca).is_file():
            raise ImproperlyConfigured("El certificado CA de MySQL no existe.")
        DATABASES["default"]["OPTIONS"]["ssl"] = {"ca": ssl_ca}
        DATABASES["default"]["OPTIONS"]["ssl_mode"] = "VERIFY_IDENTITY" if verify_tls else "REQUIRED"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "login"
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = PRODUCTION
CSRF_COOKIE_SECURE = PRODUCTION
SECURE_SSL_REDIRECT = PRODUCTION
SECURE_HSTS_SECONDS = 31536000 if PRODUCTION else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = PRODUCTION
SECURE_HSTS_PRELOAD = PRODUCTION
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
# Únicamente el proxy configurado puede alcanzar el puerto privado del contenedor.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if PRODUCTION else None
STATIC_URL = "/static/"
STATIC_ROOT = WEB_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # La construcción de imagen genera también el manifiesto, sin necesitar
    # credenciales de producción ni una conexión a MySQL durante el build.
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage" if PRODUCTION or os.environ.get("MESSI_WEB_BUILD_STATIC") == "1" else "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 250
MESSI_LOGIN_MAX_ATTEMPTS = positive_int("MESSI_WEB_LOGIN_MAX_ATTEMPTS", 5)
MESSI_LOGIN_IP_MAX_ATTEMPTS = positive_int("MESSI_WEB_LOGIN_IP_MAX_ATTEMPTS", 30)
MESSI_LOGIN_WINDOW_SECONDS = positive_int("MESSI_WEB_LOGIN_WINDOW_SECONDS", 300)
MESSI_LOGIN_BLOCK_SECONDS = positive_int("MESSI_WEB_LOGIN_BLOCK_SECONDS", 300)
MESSI_MODEL_PATH = BASE_DIR / "models" / "messi_demo.joblib"
