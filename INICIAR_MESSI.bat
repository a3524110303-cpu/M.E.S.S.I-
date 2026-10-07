@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Primero ejecuta INSTALAR_MESSI.bat.
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" messi_desktop.py
