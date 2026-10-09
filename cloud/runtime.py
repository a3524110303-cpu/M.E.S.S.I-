"""Inicialización del ORM compartido desde los secretos de Community Cloud."""

import hashlib
import ipaddress
import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "src", ROOT / "web"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

_LOCK = threading.RLock()
_CONFIG_DIGEST = None
_MIGRATIONS_CHECKED = False
_MODEL_READY = None


class CloudConfigurationError(ValueError):
    """Mensaje sin valores privados, apto para mostrar al administrador."""


def _csv(value):
    if isinstance(value, (list, tuple)):
        return ",".join(str(item).strip() for item in value)
    return str(value).strip()


def configuration_environment(section, local_test=False):
    """Valida valores sin tocar Django, archivos, conexión o estado de sesión."""
    mapping = {
        "secret_key": "MESSI_WEB_SECRET_KEY", "db_host": "MESSI_WEB_DB_HOST",
        "db_name": "MESSI_WEB_DB_NAME", "db_user": "MESSI_WEB_DB_USER",
        "db_password": "MESSI_WEB_DB_PASSWORD", "allowed_hosts": "MESSI_WEB_ALLOWED_HOSTS",
        "csrf_trusted_origins": "MESSI_WEB_CSRF_TRUSTED_ORIGINS",
    }
    values = {}
    missing = []
    for key, variable in mapping.items():
        value = _csv(section.get(key, ""))
        if not value or value.startswith("CAMBIAR_"):
            missing.append(key)
        values[variable] = value
    if missing:
        raise CloudConfigurationError("Completa la sección [messi_web] en Secrets: " + ", ".join(missing) + ".")
    try:
        port = int(section.get("db_port", 3306))
        if not 1 <= port <= 65535:
            raise ValueError
    except (TypeError, ValueError):
        raise CloudConfigurationError("db_port debe ser un puerto MySQL válido.") from None
    values["MESSI_WEB_DB_PORT"] = str(port)
    values["MESSI_WEB_ENV"] = "development" if local_test else "production"
    values["MESSI_WEB_TEST_SQLITE"] = "0"
    values["DJANGO_SETTINGS_MODULE"] = "config.settings"
    key = values["MESSI_WEB_SECRET_KEY"]
    if not local_test and (len(key) < 50 or len(set(key)) < 5 or key.startswith("django-insecure-")):
        raise CloudConfigurationError("secret_key debe ser una clave aleatoria privada de al menos 50 caracteres.")
    hosts = values["MESSI_WEB_ALLOWED_HOSTS"].split(",")
    if any(not host or "*" in host or host.startswith(".") or "://" in host for host in hosts):
        raise CloudConfigurationError("allowed_hosts necesita nombres explícitos sin protocolo ni comodines.")
    origins = values["MESSI_WEB_CSRF_TRUSTED_ORIGINS"].split(",")
    for origin in origins:
        parsed = urlparse(origin)
        if parsed.scheme != ("http" if local_test else "https") or not parsed.hostname or "*" in origin or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise CloudConfigurationError("csrf_trusted_origins necesita orígenes HTTPS exactos sin ruta ni comodines.")
    db_host = values["MESSI_WEB_DB_HOST"]
    if not local_test:
        try:
            loopback = ipaddress.ip_address(db_host).is_loopback
        except ValueError:
            loopback = db_host.lower() == "localhost"
        if loopback or db_host.startswith("/") or "://" in db_host:
            raise CloudConfigurationError("Community Cloud requiere una base MySQL externa accesible desde el servidor.")
        certificate = str(section.get("ssl_ca_pem", "")).strip()
        if not certificate.startswith("-----BEGIN CERTIFICATE-----") or "-----END CERTIFICATE-----" not in certificate or len(certificate) > 65536:
            raise CloudConfigurationError("Configura ssl_ca_pem con el certificado CA entregado por tu proveedor MySQL.")
        values["MESSI_WEB_DB_SSL_CA"] = str(ROOT / "web" / "runtime" / "cloud-mysql-ca.pem")
        values["MESSI_WEB_DB_SSL_VERIFY"] = "1"
    else:
        values["MESSI_WEB_DB_SSL_CA"] = ""
        values["MESSI_WEB_DB_SSL_VERIFY"] = "0"
    return values


def _compatible_settings(values):
    from django.conf import settings

    database = settings.DATABASES["default"]
    if database["ENGINE"] != "django.db.backends.mysql" or settings.SECRET_KEY != values["MESSI_WEB_SECRET_KEY"]:
        return False
    if settings.PRODUCTION != (values["MESSI_WEB_ENV"] == "production"):
        return False
    for field, variable in (("NAME", "MESSI_WEB_DB_NAME"), ("USER", "MESSI_WEB_DB_USER"),
                            ("PASSWORD", "MESSI_WEB_DB_PASSWORD"), ("HOST", "MESSI_WEB_DB_HOST"), ("PORT", "MESSI_WEB_DB_PORT")):
        if str(database[field]) != values[variable]:
            return False
    if values["MESSI_WEB_DB_SSL_VERIFY"] == "1":
        if database["OPTIONS"].get("ssl_mode") != "VERIFY_IDENTITY" or database["OPTIONS"].get("ssl", {}).get("ca") != values["MESSI_WEB_DB_SSL_CA"]:
            return False
    return True


def _ensure_demo_model():
    global _MODEL_READY
    if _MODEL_READY is not None:
        return _MODEL_READY
    from django.conf import settings
    from messi.model import _read_metadata

    try:
        path = settings.MESSI_MODEL_PATH
        if not path.is_file() or not path.with_suffix(".json").is_file():
            # Sólo se ejecuta código del repositorio sobre datos sintéticos.
            # No se cargan archivos binarios entregados por visitantes.
            subprocess.run([sys.executable, str(ROOT / "scripts" / "train_demo.py"), "--seed", "2026"],
                           cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=120)
        _read_metadata(path)
        _MODEL_READY = True
    except Exception:
        _MODEL_READY = False
    return _MODEL_READY


def prepare_environment(section, local_test=False):
    """Preparación explícita para comandos administrativos, sin migrar."""
    values = configuration_environment(section, local_test=local_test)
    if not local_test:
        destination = Path(values["MESSI_WEB_DB_SSL_CA"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(str(section["ssl_ca_pem"]).strip() + "\n", encoding="utf-8")
        destination.chmod(0o600)
    os.environ.update(values)
    return values


def initialize(st):
    """Configura una vez por proceso; nunca crea tablas ni cuentas al navegar."""
    global _CONFIG_DIGEST, _MIGRATIONS_CHECKED
    try:
        section = st.secrets["messi_web"]
    except Exception:
        st.error("MESSI necesita la configuración privada [messi_web] en Secrets de Streamlit Cloud.")
        return False
    local_test = os.environ.get("MESSI_CLOUD_LOCAL_TEST") == "1"
    try:
        values = configuration_environment(section, local_test=local_test)
    except CloudConfigurationError as exc:
        st.error(str(exc))
        return False
    except Exception:
        st.error("La sección [messi_web] contiene una configuración inválida.")
        return False
    certificate = str(section.get("ssl_ca_pem", "")).strip() if not local_test else ""
    digest = hashlib.sha256(json.dumps([values, certificate], sort_keys=True).encode()).hexdigest()
    with _LOCK:
        if _CONFIG_DIGEST is not None and _CONFIG_DIGEST != digest:
            st.error("La configuración cambió. Reinicia la aplicación en Community Cloud para aplicarla.")
            return False
        try:
            import django
            from django.conf import settings

            if settings.configured and not _compatible_settings(values):
                st.error("Django ya tiene otra configuración. Reinicia la aplicación antes de continuar.")
                return False
            if _CONFIG_DIGEST is None:
                prepare_environment(section, local_test=local_test)
                django.setup()
                _CONFIG_DIGEST = digest
            from django.db import close_old_connections, connections
            from django.db.migrations.executor import MigrationExecutor

            close_old_connections()
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
            if not _MIGRATIONS_CHECKED:
                executor = MigrationExecutor(connections["default"])
                if executor.migration_plan(executor.loader.graph.leaf_nodes()):
                    st.error("La base MySQL necesita sus migraciones. El administrador debe ejecutar web/manage.py migrate antes de abrir el servicio.")
                    return False
                _MIGRATIONS_CHECKED = True
            model_ready = _ensure_demo_model()
        except Exception:
            st.error("No se pudo conectar con MESSI. Revisa MySQL, TLS y los secretos privados; no se muestran datos de conexión al visitante.")
            return False
    if not model_ready:
        st.warning("El modelo demostrativo no está disponible. Las solicitudes y el seguimiento siguen funcionando.")
    return True


def administration():
    """CLI deliberada: la navegación pública nunca llama estos comandos."""
    import argparse
    import tomllib
    from django.core.management import execute_from_command_line

    parser = argparse.ArgumentParser(description="Administración MySQL remota desde un TOML privado, sin imprimir secretos.")
    parser.add_argument("action", choices=["check", "migrate", "createsuperuser"])
    parser.add_argument("--secrets", type=Path, default=ROOT / ".streamlit" / "secrets.toml")
    args = parser.parse_args()
    try:
        configuration = tomllib.loads(args.secrets.read_text(encoding="utf-8-sig"))
        prepare_environment(configuration["messi_web"])
    except CloudConfigurationError as exc:
        parser.error(str(exc))
    except Exception:
        parser.error("No se pudo leer el TOML privado de Secrets. Revisa la ruta y su estructura [messi_web].")
    options = ["--deploy", "--database", "default"] if args.action == "check" else []
    try:
        execute_from_command_line([str(ROOT / "web" / "manage.py"), args.action, *options])
    except Exception:
        print("El comando administrativo falló. Revisa MySQL, permisos y TLS; los detalles privados no se imprimen.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(administration())
