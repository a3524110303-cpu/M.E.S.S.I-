"""Inicializa únicamente MySQL, sin abrir la interfaz ni ejecutar el modelo."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from messi.database import DatabaseError, MySQLConfig, MySQLDatabase


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create-database", action="store_true", help="Crear también la base si el usuario tiene permiso CREATE")
    argumentos = parser.parse_args()
    try:
        configuracion = MySQLConfig.from_environment(ROOT)
        MySQLDatabase(configuracion).initialize(create_database=argumentos.create_database)
    except (DatabaseError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(f"Esquema MySQL de MESSI preparado en {configuracion.database}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
