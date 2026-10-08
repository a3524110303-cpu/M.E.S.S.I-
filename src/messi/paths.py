"""Recursos incluidos y datos por usuario, independientes del directorio actual."""
import os
import sys
from pathlib import Path


def resource_root() -> Path:
    """Encontrar los recursos del repositorio o los incluidos por PyInstaller."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))


def data_directory() -> Path:
    """Ubicar los datos por usuario, con una ruta alternativa para pruebas."""
    override = os.environ.get("MESSI_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share")) / "MESSI"


def database_path() -> Path:
    """Devolver el archivo SQLite persistente dentro del directorio de datos."""
    return data_directory() / "data" / "messi.sqlite3"
