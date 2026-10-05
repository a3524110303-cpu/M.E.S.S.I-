"""Migra el SQLite de MESSI a un MySQL ya inicializado, conservando el original."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from messi.database import DatabaseError, MySQLConfig, MySQLDatabase
from messi.migration import MigrationError, migrate_sqlite


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data" / "private" / "messi.sqlite3")
    args = parser.parse_args()
    try:
        resultado = migrate_sqlite(args.source, MySQLDatabase(MySQLConfig.from_environment(ROOT)))
    except (DatabaseError, MigrationError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    if resultado.get("already_applied"):
        print("La migración de SQLite ya estaba aplicada. No se duplicaron registros.")
    else:
        print("Migración completada:", ", ".join(f"{tabla}: {cantidad}" for tabla, cantidad in resultado.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
