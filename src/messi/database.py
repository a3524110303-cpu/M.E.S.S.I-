"""Configuración y transacciones MySQL de MESSI, sin conexiones al importar."""
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import threading


class DatabaseError(RuntimeError):
    """Error de almacenamiento apto para mostrar sin revelar credenciales."""


@dataclass(frozen=True)
class MySQLConfig:
    host: str = "127.0.0.1"
    port: int = 3306
    user: str = "messi"
    password: str = field(default="", repr=False)
    database: str = "messi"

    def __post_init__(self):
        if not isinstance(self.database, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", self.database):
            raise DatabaseError("El nombre de la base debe contener letras, números y guion bajo.")
        if not isinstance(self.host, str) or not self.host.strip() or not isinstance(self.user, str) or not self.user.strip():
            raise DatabaseError("Completa el servidor y el usuario de MySQL en .env.")
        if isinstance(self.port, bool) or not isinstance(self.port, int) or not 1 <= self.port <= 65535:
            raise DatabaseError("El puerto de MySQL debe estar entre 1 y 65535.")
        if not isinstance(self.password, str):
            raise DatabaseError("La contraseña de MySQL debe ser texto.")

    @classmethod
    def from_environment(cls, root: Path | None = None):
        root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
        valores = {}
        ruta = root / ".env"
        if ruta.exists():
            try:
                from dotenv import dotenv_values
                valores = dotenv_values(ruta, interpolate=False)
            except ImportError as error:
                raise DatabaseError("Instala las dependencias de MESSI para leer .env.") from error
        def valor(nombre, defecto=None):
            return os.environ.get(nombre, valores.get(nombre, defecto))
        if valor("MESSI_MYSQL_PASSWORD") is None:
            raise DatabaseError("Configura MySQL: copia .env.example a .env y completa usuario y contraseña.")
        try:
            puerto = int(valor("MESSI_MYSQL_PORT", "3306"))
        except (ValueError, TypeError) as error:
            raise DatabaseError("MESSI_MYSQL_PORT debe ser un número entero.") from error
        return cls(host=valor("MESSI_MYSQL_HOST", "127.0.0.1"), port=puerto,
                   user=valor("MESSI_MYSQL_USER", "messi"), password=valor("MESSI_MYSQL_PASSWORD"),
                   database=valor("MESSI_MYSQL_DATABASE", "messi"))


class _Connection:
    """Interfaz pequeña con cursores dict; todos se cierran con la conexión."""
    def __init__(self, raw):
        self.raw = raw
        self._cursors = []

    def execute(self, sql, params=()):
        cursor = self.raw.cursor(dictionary=True, buffered=True)
        self._cursors.append(cursor)
        cursor.execute(sql, params)
        return cursor

    def executemany(self, sql, params):
        cursor = self.raw.cursor(dictionary=True, buffered=True)
        self._cursors.append(cursor)
        cursor.executemany(sql, params)
        return cursor

    def close(self):
        try:
            for cursor in self._cursors:
                cursor.close()
        finally:
            self.raw.close()


_SCHEMA = Path(__file__).with_name("esquema_mysql.sql")
_SCHEMA_VERSION = 1
_schema_lock = threading.RLock()


def _driver():
    try:
        import mysql.connector
        return mysql.connector
    except ImportError as error:
        raise DatabaseError("Instala las dependencias de MESSI para utilizar MySQL.") from error


def _safe_error(error):
    codigo = getattr(error, "errno", None)
    if codigo in (1044, 1045, 1142):
        return DatabaseError("MySQL rechazó el acceso. Revisa el usuario, la contraseña y sus permisos en .env.")
    if codigo == 1049:
        return DatabaseError("La base MySQL no existe. Ejecuta scripts/init_database.py --create-database.")
    if codigo in (1146, 1054):
        return DatabaseError("Falta el esquema de MESSI. Ejecuta scripts/init_database.py con el usuario de instalación.")
    if codigo in (2003, 2005, 2006, 2013, 2055):
        return DatabaseError("No se pudo conectar con MySQL. Comprueba el servidor, el puerto y que esté activo.")
    return DatabaseError("MySQL no pudo completar la operación; no se confirmó la transacción.")


class MySQLDatabase:
    def __init__(self, config: MySQLConfig):
        self.config = config

    def _open(self, with_database=True):
        driver = _driver()
        argumentos = dict(host=self.config.host, port=self.config.port, user=self.config.user,
                          password=self.config.password, charset="utf8mb4", collation="utf8mb4_0900_ai_ci",
                          autocommit=False, connection_timeout=5, read_timeout=10, write_timeout=10,
                          allow_local_infile=False)
        if with_database:
            argumentos["database"] = self.config.database
        try:
            return _Connection(driver.connect(**argumentos))
        except driver.Error as error:
            raise _safe_error(error) from error

    @contextmanager
    def connection(self):
        """Operaciones de datos únicamente: no crean tablas ni bases."""
        driver = _driver()
        db = self._open()
        try:
            version = db.execute("SELECT version FROM schema_migrations WHERE version = %s", (_SCHEMA_VERSION,)).fetchone()
            if version is None:
                raise DatabaseError("Inicializa el esquema de MESSI con scripts/init_database.py.")
            # La lectura del marcador ya abrió transacción; comenzar operación separada.
            db.raw.rollback()
            db.raw.start_transaction(isolation_level="REPEATABLE READ")
            yield db
            db.raw.commit()
        except driver.Error as error:
            db.raw.rollback()
            raise _safe_error(error) from error
        except BaseException:
            db.raw.rollback()
            raise
        finally:
            db.close()

    def initialize(self, create_database=False):
        """DDL de instalación explícito. MySQL confirma DDL por separado de los datos."""
        driver = _driver()
        with _schema_lock:
            if create_database:
                servidor = self._open(with_database=False)
                try:
                    servidor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.config.database}` "
                                     "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
                except driver.Error as error:
                    raise _safe_error(error) from error
                finally:
                    servidor.close()
            db = self._open()
            lock_name = "messi_schema_" + hashlib.sha256(self.config.database.encode()).hexdigest()[:40]
            bloqueado = False
            try:
                resultado = db.execute("SELECT VERSION() AS version").fetchone()["version"]
                version = tuple(int(p) for p in resultado.split("-")[0].split(".")[:3])
                if "MariaDB" in resultado or version < (8, 0, 16):
                    raise DatabaseError("MESSI requiere MySQL 8.0.16 o posterior.")
                bloqueado = db.execute("SELECT GET_LOCK(%s, 10) AS adquirido", (lock_name,)).fetchone()["adquirido"] == 1
                if not bloqueado:
                    raise DatabaseError("Otra instalación está preparando el esquema. Vuelve a intentar.")
                db.raw.autocommit = True
                # El esquema usa sentencias simples; no contiene rutinas ni DELIMITER.
                sql = "\n".join(l for l in _SCHEMA.read_text(encoding="utf-8").splitlines() if not l.lstrip().startswith("--"))
                for sentencia in sql.split(";"):
                    if sentencia.strip():
                        db.execute(sentencia)
                db.execute("INSERT INTO schema_migrations(version, description, applied_at) "
                           "VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE version = version",
                           (_SCHEMA_VERSION, "Esquema relacional MySQL MESSI", datetime.now(timezone.utc).isoformat()))
            except driver.Error as error:
                raise _safe_error(error) from error
            finally:
                try:
                    if bloqueado:
                        db.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
                finally:
                    db.close()
