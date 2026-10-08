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
    """Gestionar un servidor loopback y detenerlo al cerrar el proceso principal."""

    def __init__(self):
        """Preparar el estado de un único arranque y registrar su cierre final."""
        self.process = None
        self.url = None
        self._job = None
        self._log = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        atexit.register(self.close)

    def start(self):
        """Lanzar el servidor incluido y esperar su comprobación de salud."""
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
        try:
            # Cerrar la ventana durante el arranque no debe dejar un proceso
            # nuevo después de que close() haya terminado.
            with self._lock:
                if self._stop.is_set():
                    raise RuntimeError("El inicio de MESSI fue cancelado.")
                if self.process is not None:
                    raise RuntimeError("Este servidor de MESSI ya fue iniciado.")
                self._log = open(directory / "logs" / "servidor.log", "a", encoding="utf-8")
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
        """Cancelar el inicio o terminar el servidor y liberar registro y Job."""
        self._stop.set()
        with self._lock:
            try:
                if self.process and self.process.poll() is None:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                        self.process.wait(timeout=5)
            finally:
                if self._job:
                    from messi.windows_process import close_job
                    close_job(self._job)
                    self._job = None
                if self._log:
                    self._log.close()
                    self._log = None


def run_server(port):
    """Servir la aplicación incluida sólo en esta computadora, sin telemetría."""
    if not 1024 <= port <= 65535:
        raise ValueError("Puerto local inválido.")
    from streamlit.web import bootstrap
    options = {
        "server.address": "127.0.0.1", "server.port": port, "server.headless": True,
        "server.fileWatcherType": "none", "server.maxUploadSize": 5,
        "browser.gatherUsageStats": False, "global.developmentMode": False,
        "client.toolbarMode": "viewer", "theme.base": "light", "theme.primaryColor": "#167A72",
        "theme.backgroundColor": "#F5F8F7", "theme.secondaryBackgroundColor": "#F8FBFA",
        "theme.textColor": "#122C39",
    }
    bootstrap.load_config_options(options)
    bootstrap.run(str(resource_root() / "app.py"), False, [], options)


def run_window():
    """Mostrar arranque, reapertura del navegador, respaldo y diagnóstico local."""
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from messi.sqlite_storage import SQLiteStore
    from messi.paths import database_path

    window = tk.Tk()
    window.title("MESSI · Sistema local")
    window.geometry("620x460")
    window.resizable(False, False)
    navy, teal, paper, amber = "#122C39", "#167A72", "#F5F8F7", "#D99535"
    muted, border = "#536872", "#DCE6E2"
    window.configure(background=paper)
    style = ttk.Style(window)
    style.theme_use("clam")
    style.configure("MESSI.TFrame", background=paper)
    style.configure("MESSI.Card.TFrame", background="white")
    style.configure("MESSI.TLabel", background=paper, foreground=navy, font=("Segoe UI", 10))
    style.configure("MESSI.Hint.TLabel", background=paper, foreground=muted, font=("Segoe UI", 9))
    style.configure("MESSI.Card.TLabel", background="white", foreground=muted, font=("Segoe UI", 10))
    style.configure("MESSI.Primary.TButton", background=teal, foreground="white",
                    font=("Segoe UI", 11, "bold"), padding=(16, 10), borderwidth=0, focusthickness=2,
                    focuscolor="#A45D13")
    style.map("MESSI.Primary.TButton", background=[("disabled", "#D4E2DE"), ("pressed", "#105C56"), ("active", "#126D65")],
              foreground=[("disabled", "#586F69")])
    style.configure("MESSI.Secondary.TButton", background="white", foreground=navy,
                    font=("Segoe UI", 10), padding=(12, 8), borderwidth=1, bordercolor=border,
                    focusthickness=2, focuscolor=teal)
    style.map("MESSI.Secondary.TButton", background=[("pressed", "#E0ECE7"), ("active", "#EDF4F0")])
    style.configure("MESSI.Close.TButton", background=paper, foreground=navy,
                    font=("Segoe UI", 10), padding=(12, 7), borderwidth=1, bordercolor=border,
                    focusthickness=2, focuscolor="#A45D13")
    style.map("MESSI.Close.TButton", background=[("pressed", "#E9E4D8"), ("active", "#F4ECDC")])

    brand = tk.Frame(window, background=navy)
    brand.pack(fill="x")
    tk.Label(brand, text="MESSI", font=("Segoe UI", 24, "bold"), background=navy,
             foreground="white").pack(anchor="w", padx=24, pady=(12, 0))
    tk.Label(brand, text="Alerta y acompañamiento escolar", font=("Segoe UI", 10),
             background=navy, foreground="#CEE1DB").pack(anchor="w", padx=25, pady=(0, 12))

    frame = ttk.Frame(window, padding=(24, 14), style="MESSI.TFrame")
    frame.pack(fill="both", expand=True)
    state_title = tk.StringVar(value="Preparando MESSI")
    status = tk.StringVar(value="Iniciando el sistema en esta computadora…")
    state_card = ttk.Frame(frame, padding=(14, 10), style="MESSI.Card.TFrame")
    state_card.pack(fill="x")
    state_heading = tk.Frame(state_card, background="white")
    state_heading.pack(fill="x")
    state_dot = tk.Label(state_heading, text="●", foreground=amber, background="white",
                         font=("Segoe UI", 12))
    state_dot.pack(side="left", padx=(0, 7))
    tk.Label(state_heading, textvariable=state_title, foreground=navy, background="white",
             font=("Segoe UI", 11, "bold")).pack(side="left")
    ttk.Label(state_card, textvariable=status, wraplength=510, style="MESSI.Card.TLabel").pack(anchor="w", pady=(2, 0))
    events = queue.Queue()
    server = LocalServer()
    closing = threading.Event()

    def open_browser():
        """Abrir la dirección disponible o mostrarla si no hay navegador asociado."""
        if server.url and server.process and server.process.poll() is None:
            if not webbrowser.open(server.url):
                messagebox.showinfo("Abrir MESSI", f"Abre esta dirección en tu navegador:\n{server.url}", parent=window)

    open_button = ttk.Button(frame, text="Abrir MESSI", command=open_browser, state="disabled",
                             style="MESSI.Primary.TButton")
    open_button.pack(fill="x", pady=(12, 0))
    ttk.Label(frame, text="Abre las vistas Docente, Tutor y Estudiante en tu navegador.",
              style="MESSI.Hint.TLabel").pack(anchor="w", pady=(4, 0))
    ttk.Label(frame, text="Cuida tus registros", style="MESSI.TLabel",
              font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(12, 7))
    tools = ttk.Frame(frame, style="MESSI.TFrame")
    tools.pack(fill="x")
    tools.columnconfigure(0, weight=1, uniform="tools")
    tools.columnconfigure(1, weight=1, uniform="tools")

    def backup():
        """Guardar un respaldo SQLite consistente en el destino elegido."""
        destination = filedialog.asksaveasfilename(parent=window, title="Guardar respaldo de MESSI",
            defaultextension=".sqlite3", initialfile="messi-respaldo.sqlite3", filetypes=[("SQLite", "*.sqlite3")])
        if destination:
            try:
                SQLiteStore(database_path()).backup(Path(destination))
                messagebox.showinfo("Respaldo guardado", "El respaldo quedó guardado en el archivo elegido.", parent=window)
            except Exception as exc:
                messagebox.showerror("Respaldo", str(exc), parent=window)

    ttk.Button(tools, text="Guardar respaldo", command=backup,
               style="MESSI.Secondary.TButton").grid(row=0, column=0, sticky="ew", padx=(0, 6))
    ttk.Label(tools, text="Una copia de tus registros para recuperarlos después.", wraplength=250,
              style="MESSI.Hint.TLabel").grid(row=1, column=0, sticky="nw", padx=(0, 6), pady=(5, 0))

    def diagnosis():
        """Guardar un informe de dependencias e integridad sin exportar registros."""
        from messi.diagnostics import diagnose
        try:
            result = diagnose()
            path = data_directory() / "diagnostico.json"
            path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            messagebox.showinfo("Diagnóstico", f"Reporte guardado en:\n{path}\n\nEstado: {'correcto' if result['ok'] else 'requiere revisión'}", parent=window)
        except Exception as exc:
            messagebox.showerror("Diagnóstico", str(exc), parent=window)

    ttk.Button(tools, text="Guardar diagnóstico", command=diagnosis,
               style="MESSI.Secondary.TButton").grid(row=0, column=1, sticky="ew", padx=(6, 0))
    ttk.Label(tools, text="Un reporte técnico para que el equipo te ayude.", wraplength=250,
              style="MESSI.Hint.TLabel").grid(row=1, column=1, sticky="nw", padx=(6, 0), pady=(5, 0))

    def close():
        """Cerrar la ventana y su servidor, también durante el inicio."""
        closing.set()
        server.close()
        window.destroy()

    tk.Frame(frame, background=border, height=1).pack(fill="x", pady=(12, 8))
    finish = ttk.Frame(frame, style="MESSI.TFrame")
    finish.pack(fill="x")
    ttk.Label(finish, text="Al terminar, cierra MESSI desde aquí.",
              style="MESSI.Hint.TLabel").pack(side="left")
    ttk.Button(finish, text="Cerrar MESSI", command=close,
               style="MESSI.Close.TButton").pack(side="right")
    window.protocol("WM_DELETE_WINDOW", close)

    def start():
        """Inicializar SQLite y arrancar el servidor fuera del hilo de la ventana."""
        try:
            SQLiteStore(database_path())
            server.start()
            events.put((True, "MESSI está abierto en tu navegador. Mantén esta ventana abierta mientras lo usas."))
        except Exception as exc:
            events.put((False, str(exc)))

    def poll():
        """Actualizar el estado de la ventana mediante eventos del hilo de inicio."""
        if closing.is_set():
            return
        try:
            success, text = events.get_nowait()
            status.set(text)
            state_title.set("Todo listo" if success else "Revisemos el inicio")
            state_dot.configure(foreground=teal if success else amber)
            if success:
                open_button.configure(state="normal")
                open_browser()
        except queue.Empty:
            pass
        if server.process and server.process.poll() is not None:
            open_button.configure(state="disabled")
            state_title.set("MESSI se detuvo")
            state_dot.configure(foreground=amber)
            status.set("El sistema se detuvo. Guarda el diagnóstico y vuelve a abrir MESSI.")
        window.after(300, poll)

    threading.Thread(target=start, daemon=True).start()
    window.after(200, poll)
    window.mainloop()
