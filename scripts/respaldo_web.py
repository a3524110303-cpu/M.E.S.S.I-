"""Respalda/restaura MySQL de Compose o local sin contraseña en argumentos.

Requiere Docker Compose y ejecutarse desde cualquier carpeta. El .sql contiene
datos privados: mantenerlo fuera del repositorio y probar la recuperación.
"""

import argparse
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ["docker", "compose", "--env-file", str(ROOT / "web" / ".env"), "-f", str(ROOT / "compose.web.yaml")]
DUMP = 'export MYSQL_PWD="$MYSQL_PASSWORD"; exec mysqldump --user="$MYSQL_USER" --single-transaction --quick --no-tablespaces --set-gtid-purged=OFF --default-character-set=utf8mb4 "$MYSQL_DATABASE"'
RESTORE = 'export MYSQL_PWD="$MYSQL_PASSWORD"; exec mysql --user="$MYSQL_USER" --default-character-set=utf8mb4 "$MYSQL_DATABASE"'


def local_command(action, binary_directory):
    """Lee únicamente la configuración web; el secreto viaja por entorno."""
    from dotenv import load_dotenv

    load_dotenv(ROOT / "web" / ".env", override=False)
    if os.environ.get("MESSI_WEB_TEST_SQLITE") == "1":
        raise ValueError("El respaldo MySQL no se ejecuta en modo SQLite de pruebas.")
    names = ["MESSI_WEB_DB_NAME", "MESSI_WEB_DB_USER", "MESSI_WEB_DB_PASSWORD", "MESSI_WEB_DB_HOST"]
    values = {name: os.environ.get(name, "").strip() for name in names}
    if any(not value or value.startswith("CAMBIAR_") for value in values.values()):
        raise ValueError("Completa MESSI_WEB_DB_* en web/.env para el respaldo local.")
    port = int(os.environ.get("MESSI_WEB_DB_PORT", "3306"))
    if not 1 <= port <= 65535:
        raise ValueError("El puerto MySQL no es válido.")
    binary_name = "mysqldump" if action == "backup" else "mysql"
    executable = shutil.which(binary_name)
    if binary_directory:
        executable = str(binary_directory / (binary_name + (".exe" if os.name == "nt" else "")))
    elif not executable and os.name == "nt":
        candidate = Path(r"C:\Program Files\MySQL\MySQL Server 8.0\bin") / (binary_name + ".exe")
        if candidate.is_file():
            executable = str(candidate)
    if not executable or not Path(executable).is_file():
        raise ValueError("Instala los clientes MySQL o indica --mysql-bin-dir.")
    command = [executable, "--no-defaults", "--host=" + values["MESSI_WEB_DB_HOST"],
               "--port=" + str(port), "--user=" + values["MESSI_WEB_DB_USER"], "--default-character-set=utf8mb4"]
    if action == "backup":
        command += ["--single-transaction", "--quick", "--no-tablespaces", "--set-gtid-purged=OFF"]
    command.append(values["MESSI_WEB_DB_NAME"])
    child_environment = os.environ.copy()
    child_environment["MYSQL_PWD"] = values["MESSI_WEB_DB_PASSWORD"]
    return command, child_environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["backup", "restore"])
    parser.add_argument("--file", type=Path, help="Ruta del .sql (obligatoria al restaurar).")
    parser.add_argument("--confirm-replace", action="store_true", help="Autoriza reemplazar los datos del servidor al restaurar.")
    parser.add_argument("--local", action="store_true", help="Usa clientes MySQL del equipo y web/.env, sin Docker.")
    parser.add_argument("--mysql-bin-dir", type=Path, help="Carpeta de mysql y mysqldump para --local.")
    args = parser.parse_args()
    if args.mysql_bin_dir and not args.local:
        parser.error("--mysql-bin-dir requiere --local.")
    try:
        if args.local:
            command, environment = local_command(args.action, args.mysql_bin_dir)
        else:
            command = COMPOSE + ["exec", "-T", "db", "sh", "-c", DUMP if args.action == "backup" else RESTORE]
            environment = None
    except ValueError as exc:
        parser.error(str(exc))
    if args.action == "restore":
        if not args.file or not args.confirm_replace:
            parser.error("Restaurar requiere --file y --confirm-replace. Detén app y caddy antes de restaurar.")
        target = args.file.resolve(strict=True)
        with target.open("rb") as stream:
            subprocess.run(command, stdin=stream, env=environment, stderr=subprocess.PIPE, check=True)
        print("Restauración completada. Revisa las migraciones antes de iniciar la aplicación.")
    else:
        target = (args.file or ROOT / "backups" / ("messi-web-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".sql")).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        # 'xb' evita destruir un respaldo existente; un fallo borra sólo el
        # archivo recién creado e incompleto.
        with target.open("xb") as stream:
            try:
                subprocess.run(command, stdout=stream, env=environment, stderr=subprocess.PIPE, check=True)
            except BaseException:
                stream.close()
                target.unlink(missing_ok=True)
                raise
        print(f"Respaldo guardado en {target}")


if __name__ == "__main__":
    main()
