"""Comprobación del paquete sin leer ni divulgar datos personales."""
import importlib.metadata
import json
import os
import platform
import sqlite3
import tempfile
from pathlib import Path

from messi.paths import database_path, resource_root
from messi.sqlite_storage import SQLiteStore


def diagnose():
    info = {"version": "0.2.0-local", "windows": platform.platform(),
            "arquitectura": platform.machine(), "sqlite": sqlite3.sqlite_version,
            "base_local": str(database_path()), "modelo": "MLP de demostración sintética",
            "dependencias": {}, "errores": []}
    for name in ("streamlit", "scikit-learn", "numpy", "scipy", "pandas", "joblib", "openpyxl", "pyarrow"):
        try:
            info["dependencias"][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            info["errores"].append(f"Falta {name}")
    try:
        store = SQLiteStore(database_path())
        with store._connection() as db:
            info["integridad_sqlite"] = db.execute("PRAGMA integrity_check").fetchone()[0]
            info["integridad_relaciones"] = len(db.execute("PRAGMA foreign_key_check").fetchall()) == 0
        from messi.data import load_csv
        from messi.model import score_records
        records = load_csv(resource_root() / "data" / "synthetic" / "students_demo.csv")
        info["predicciones_comprobadas"] = len(score_records(records, resource_root() / "models" / "messi_demo.joblib"))
    except Exception as exc:
        info["errores"].append(str(exc))
    info["ok"] = not info["errores"] and info.get("integridad_sqlite") == "ok" and info.get("integridad_relaciones", False)
    return info


def self_test():
    info = diagnose()
    try:
        from messi.data import load_csv
        from messi.model import score_records
        from streamlit.testing.v1 import AppTest
        records = load_csv(resource_root() / "data" / "synthetic" / "students_demo.csv")
        predictions = score_records(records, resource_root() / "models" / "messi_demo.joblib")
        with tempfile.TemporaryDirectory() as directory:
            previous = os.environ.get("MESSI_DATA_DIR")
            os.environ["MESSI_DATA_DIR"] = directory
            try:
                path = database_path()
                store = SQLiteStore(path)
                store.save_indicators(records)
                store.save_predictions(predictions)
                request = store.create_request("EST-001", "Solicitud ficticia de prueba")
                support = store.create_support("EST-001", "Tutoria", "Apoyo ficticio de prueba")
                store.add_followup(support, "Seguimiento ficticio", "Cerrado")
                reopened = SQLiteStore(path)
                assert reopened.list_indicators() == records
                assert reopened.list_predictions() == predictions
                assert reopened.list_requests()[0]["id"] == request
                assert reopened.list_supports()[0]["status"] == "Cerrado"
                assert reopened.list_followups(support)[0]["notes"] == "Seguimiento ficticio"
                backup = Path(directory) / "respaldo.sqlite3"
                reopened.backup(backup)
                assert SQLiteStore(backup).list_predictions() == predictions
                info["flujo_persistencia"] = "OK"
                ui = AppTest.from_file(str(resource_root() / "app.py"), default_timeout=30).run()
                assert not ui.exception, str(ui.exception)
                ui.radio[0].set_value("Ejemplo sintético").run()
                next(button for button in ui.button if button.label == "Cargar ejemplo sintético").click().run()
                next(button for button in ui.button if button.label == "Calcular riesgo de demostración").click().run()
                assert not ui.exception, str(ui.exception)
                assert ui.session_state["predictions"] == predictions
                assert SQLiteStore(path).list_predictions() == predictions
                for role in ("Tutor", "Estudiante", "Docente"):
                    ui.sidebar.radio[0].set_value(role).run()
                    assert not ui.exception, str(ui.exception)
                fresh = AppTest.from_file(str(resource_root() / "app.py"), default_timeout=30).run()
                fresh.sidebar.radio[0].set_value("Tutor").run()
                assert not fresh.exception, str(fresh.exception)
                assert fresh.session_state["predictions"] == predictions
                info["pantallas"] = "Docente, Tutor y Estudiante: OK"
                info["inferencia_en_interfaz_y_reapertura"] = "OK"
            finally:
                if previous is None:
                    os.environ.pop("MESSI_DATA_DIR", None)
                else:
                    os.environ["MESSI_DATA_DIR"] = previous
    except Exception as exc:
        info["errores"].append(str(exc) or type(exc).__name__)
        info["ok"] = False
    return info
