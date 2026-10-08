"""Entrada del ejecutable MESSI para Windows 10/11 y diagnósticos de construcción."""
import argparse
import json
import multiprocessing
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))


def main():
    """Elegir ventana, servidor o verificación y devolver un código de salida."""
    parser = argparse.ArgumentParser(description="MESSI local")
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=8501, help=argparse.SUPPRESS)
    parser.add_argument("--diagnostico", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--smoke-server", action="store_true")
    parser.add_argument("--salida", type=Path)
    args = parser.parse_args()
    from messi.paths import data_directory
    logs = data_directory() / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    if sys.stdout is None:
        sys.stdout = open(logs / "aplicacion.log", "a", encoding="utf-8", buffering=1)
    if sys.stderr is None:
        sys.stderr = sys.stdout
    try:
        from messi.desktop import run_server, run_window
        if args.serve:
            run_server(args.port)
        elif args.self_test or args.diagnostico or args.smoke_server:
            from messi.diagnostics import diagnose, self_test, smoke_server
            result = self_test() if args.self_test else smoke_server() if args.smoke_server else diagnose()
            output = args.salida or data_directory() / "diagnostico.json"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0 if result["ok"] else 1
        else:
            run_window()
        return 0
    except Exception as exc:
        traceback.print_exc()
        if not (args.serve or args.self_test or args.diagnostico or args.smoke_server):
            import tkinter as tk
            from tkinter import messagebox
            window = tk.Tk()
            window.withdraw()
            messagebox.showerror("No pude iniciar MESSI", f"{exc}\n\nRegistros: {logs}", parent=window)
            window.destroy()
        return 1


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
