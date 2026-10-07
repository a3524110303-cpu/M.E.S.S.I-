"""Arranque del servidor incluido y ventana de control para el cliente."""
from __future__ import annotations
import atexit
import json
import os
from pathlib import Path
import queue
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

from messi.paths import data_directory, resource_root


class LocalServer:
    def __init__(self):
        self.process = None
        self.url = None
        self._job = None
        self._log = None
        self._stop = threading.Event()
        atexit.register(self.close)

    def start(self):
        directory = data_directory()
        (directory / "logs").mkdir(parents=True, exist_ok=True)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.url = f"http://127.0.0.1:{port}"
        args = [sys.executable]
        if not getattr(sys, "frozen", False):
            args.append(str(resource_root() / "messi_desktop.py"))
        args += ["--serve", "--port", str(port)]
        self._log = open(directory / "logs" / "servidor.log", "a", encoding="utf-8")
        try:
            self.process = subprocess.Popen(args, cwd=directory, stdin=subprocess.DEVNULL,
                stdout=self._log, stderr=self._log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            if os.name == "nt":
                from messi.windows_process import protect_process
                self._job = protect_process(self.process)
            # Ignorar proxies del equipo: todo el tráfico va a loopback.
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline and not self._stop.is_set():
                if self.process.poll() is not None:
                    raise RuntimeError("El servidor local no inició. Consulta el diagnóstico y el registro de servidor.")
                try:
                    with opener.open(self.url + "/_stcore/health", timeout=2) as result:
                        if result.status == 200 and result.read() == b"ok":
                            return
                except (OSError, urllib.error.URLError):
                    pass
                self._stop.wait(0.3)
            raise RuntimeError("No se completó el inicio de MESSI. Cierra la ventana y vuelve a abrir el sistema.")
        except Exception:
            self.close()
            raise

    def close(self):
        self._stop.set()
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        if self._job:
            from messi.windows_process import close_job
            close_job(self._job)
            self._job = None
        if self._log:
            self._log.close()
            self._log = None


def run_server(port):
    if not 1024 <= port <= 65535:
        raise ValueError("Puerto local inválido.")
    from streamlit.web import bootstrap
    options = {
        "server.address": "127.0.0.1", "server.port": port, "server.headless": True,
        "server.fileWatcherType": "none", "server.maxUploadSize": 5,
        "browser.gatherUsageStats": False, "global.developmentMode": False,
        "client.toolbarMode": "viewer", "theme.base": "light", "theme.primaryColor": "#225D54",
    }
    bootstrap.load_config_options(options)
    bootstrap.run(str(resource_root() / "app.py"), False, [], options)


def run_window():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from messi.sqlite_storage import SQLiteStore
    from messi.paths import database_path

    window = tk.Tk()
    window.title("MESSI · Sistema local")
    window.geometry("550x360")
    window.resizable(False, False)
    frame = ttk.Frame(window, padding=24)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="MESSI", font=("Segoe UI", 24, "bold")).pack(anchor="w")
    ttk.Label(frame, text="Alerta y acompañamiento escolar", font=("Segoe UI", 12)).pack(anchor="w", pady=(0, 16))
    status = tk.StringVar(value="Iniciando el sistema en esta computadora…")
    ttk.Label(frame, textvariable=status, wraplength=490).pack(anchor="w", pady=(0, 16))
    events = queue.Queue()
    server = LocalServer()
    closing = threading.Event()

    def open_browser():
        if server.url and server.process and server.process.poll() is None:
            if not webbrowser.open(server.url):
                messagebox.showinfo("Abrir MESSI", f"Abre esta dirección en tu navegador:\n{server.url}", parent=window)

    open_button = ttk.Button(frame, text="Abrir MESSI", command=open_browser, state="disabled")
    open_button.pack(fill="x", pady=4)

    def backup():
        destination = filedialog.asksaveasfilename(parent=window, title="Guardar respaldo de MESSI",
            defaultextension=".sqlite3", initialfile="messi-respaldo.sqlite3", filetypes=[("SQLite", "*.sqlite3")])
        if destination:
            try:
                SQLiteStore(database_path()).backup(Path(destination))
                messagebox.showinfo("Respaldo guardado", "El respaldo quedó guardado en el archivo elegido.", parent=window)
            except Exception as exc:
                messagebox.showerror("Respaldo", str(exc), parent=window)

    ttk.Button(frame, text="Guardar respaldo", command=backup).pack(fill="x", pady=4)

    def diagnosis():
        from messi.diagnostics import diagnose
        try:
            result = diagnose()
            path = data_directory() / "diagnostico.json"
            path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            messagebox.showinfo("Diagnóstico", f"Reporte guardado en:\n{path}\n\nEstado: {'correcto' if result['ok'] else 'requiere revisión'}", parent=window)
        except Exception as exc:
            messagebox.showerror("Diagnóstico", str(exc), parent=window)

    ttk.Button(frame, text="Guardar diagnóstico", command=diagnosis).pack(fill="x", pady=4)

    def close():
        closing.set()
        server.close()
        window.destroy()

    ttk.Button(frame, text="Cerrar MESSI", command=close).pack(fill="x", pady=4)
    window.protocol("WM_DELETE_WINDOW", close)

    def start():
        try:
            SQLiteStore(database_path())
            server.start()
            events.put((True, "MESSI está abierto en tu navegador. Mantén esta ventana abierta mientras lo usas."))
        except Exception as exc:
            events.put((False, str(exc)))

    def poll():
        if closing.is_set():
            return
        try:
            success, text = events.get_nowait()
            status.set(text)
            if success:
                open_button.configure(state="normal")
                open_browser()
        except queue.Empty:
            pass
        if server.process and server.process.poll() is not None:
            open_button.configure(state="disabled")
            status.set("El sistema se detuvo. Guarda el diagnóstico y vuelve a abrir MESSI.")
        window.after(300, poll)

    threading.Thread(target=start, daemon=True).start()
    window.after(200, poll)
    window.mainloop()
