"""Administración de cuentas de equipo MESSI con credenciales exclusivas del administrador."""
import argparse
from dataclasses import replace
import getpass
import hashlib
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from messi.database import DatabaseError, MySQLConfig, MySQLDatabase, _driver, _safe_error


def role_names(database):
    prefijo = "messi_" + database[:8] + "_" + hashlib.sha256(database.encode()).hexdigest()[:6]
    return {"lector": prefijo + "_lector", "editor": prefijo + "_editor"}


def _require_managed_grants(db, username, user_host, roles):
    grantee = f"'{username}'@'{user_host}'"
    # Un cambio a lector no sirve si conserva permisos directos u otros roles.
    for tabla in ("USER_PRIVILEGES", "SCHEMA_PRIVILEGES", "TABLE_PRIVILEGES", "COLUMN_PRIVILEGES"):
        permiso = db.execute(
            f"SELECT PRIVILEGE_TYPE FROM information_schema.{tabla} "
            "WHERE GRANTEE = %s AND PRIVILEGE_TYPE <> 'USAGE' LIMIT 1", (grantee,)
        ).fetchone()
        if permiso:
            raise DatabaseError("Esta cuenta tiene permisos directos. Usa una cuenta creada con esta herramienta "
                                "o retira primero los permisos anteriores como administrador.")
    otros = db.execute("SELECT FROM_USER AS rol, FROM_HOST AS origen FROM mysql.role_edges "
                       "WHERE TO_USER = %s AND TO_HOST = %s", (username, user_host)).fetchall()
    if any(fila["rol"] not in roles.values() or fila["origen"] != "%" for fila in otros):
        raise DatabaseError("Esta cuenta tiene otros roles. Revisa sus permisos antes de modificarla desde MESSI.")


def manage(config, action, username=None, user_host="127.0.0.1", role="editor", password=None):
    """Aplica roles acotados a esta base, sin otorgar administración al equipo."""
    if action not in {"create", "set-role", "block", "unblock", "list"}:
        raise DatabaseError("Acción de administración inválida.")
    if action != "list" and (not isinstance(username, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,31}", username)):
        raise DatabaseError("El usuario debe tener hasta 32 letras, números o guiones bajos.")
    if not isinstance(user_host, str) or not re.fullmatch(r"[A-Za-z0-9_.:%-]+", user_host):
        raise DatabaseError("El origen del usuario de MySQL es inválido.")
    if role not in {"lector", "editor"}:
        raise DatabaseError("Selecciona el rol lector o editor.")
    if action == "create" and (not isinstance(password, str) or not password):
        raise DatabaseError("La cuenta nueva necesita una contraseña.")
    if action != "list" and username == config.user:
        raise DatabaseError("Utiliza una cuenta de equipo distinta de la cuenta administradora.")
    roles = role_names(config.database)
    driver = _driver()
    db = MySQLDatabase(config)._open()
    try:
        db.raw.autocommit = True
        if action == "list":
            return db.execute(
                "SELECT e.TO_USER AS usuario, e.TO_HOST AS origen, e.FROM_USER AS rol, "
                "u.account_locked AS bloqueada FROM mysql.role_edges e "
                "JOIN mysql.user u ON u.User = e.TO_USER AND u.Host = e.TO_HOST "
                "WHERE e.FROM_USER IN (%s, %s) ORDER BY e.TO_USER, e.TO_HOST",
                tuple(roles.values())
            ).fetchall()
        if action in {"block", "unblock"}:
            db.execute("ALTER USER %s@%s ACCOUNT " + ("LOCK" if action == "block" else "UNLOCK"),
                       (username, user_host))
            return []
        if action == "set-role":
            _require_managed_grants(db, username, user_host, roles)
        for nombre in roles.values():
            db.execute("CREATE ROLE IF NOT EXISTS %s", (nombre,))
        db.execute(f"GRANT SELECT ON `{config.database}`.* TO %s", (roles["lector"],))
        db.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON `{config.database}`.* TO %s", (roles["editor"],))
        if action == "create":
            db.execute("CREATE USER %s@%s IDENTIFIED BY %s", (username, user_host, password))
        membresias = db.execute(
            "SELECT FROM_USER AS rol FROM mysql.role_edges WHERE TO_USER = %s AND TO_HOST = %s "
            "AND FROM_USER IN (%s, %s)", (username, user_host, *roles.values())
        ).fetchall()
        # Primero otorgar el rol solicitado; luego retirar el rol anterior.
        db.execute("GRANT %s TO %s@%s", (roles[role], username, user_host))
        for anterior in membresias:
            if anterior["rol"] != roles[role]:
                db.execute("REVOKE %s FROM %s@%s", (anterior["rol"], username, user_host))
        db.execute("SET DEFAULT ROLE %s TO %s@%s", (roles[role], username, user_host))
        return []
    except driver.Error as error:
        raise _safe_error(error) from error
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "set-role", "block", "unblock", "list"))
    parser.add_argument("user", nargs="?")
    parser.add_argument("--role", choices=("lector", "editor"), default="editor")
    parser.add_argument("--user-host", default="127.0.0.1")
    parser.add_argument("--admin-user", default=os.environ.get("MESSI_MYSQL_ADMIN_USER", "root"))
    args = parser.parse_args()
    try:
        config = MySQLConfig.from_environment(ROOT)
        admin_password = os.environ.get("MESSI_MYSQL_ADMIN_PASSWORD")
        if admin_password is None:
            admin_password = getpass.getpass("Contraseña del administrador MySQL: ")
        config = replace(config, user=args.admin_user, password=admin_password)
        nueva_password = None
        if args.action == "create":
            nueva_password = getpass.getpass("Contraseña del nuevo usuario: ")
            if nueva_password != getpass.getpass("Repite la contraseña del nuevo usuario: "):
                raise DatabaseError("Las contraseñas no coinciden.")
        resultados = manage(config, args.action, args.user, args.user_host, args.role, nueva_password)
        for fila in resultados:
            print(f"{fila['usuario']}@{fila['origen']}: {fila['rol']} | bloqueada: {fila['bloqueada']}")
        print("Operación de permisos completada.")
        return 0
    except (DatabaseError, OSError, EOFError, KeyboardInterrupt) as error:
        print(str(error) or "Operación interrumpida.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
