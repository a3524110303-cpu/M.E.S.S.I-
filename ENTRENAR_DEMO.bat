@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Primero ejecuta INSTALAR_MESSI.bat.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\train_demo.py
if errorlevel 1 (
  echo El entrenamiento fallo. Conserva el error para revisarlo.
  pause
  exit /b 1
)
echo Modelo de demostracion generado con datos sinteticos. No valida eficacia escolar.
pause
