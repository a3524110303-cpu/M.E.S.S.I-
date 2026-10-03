@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Instala Python 3.13 desde https://www.python.org/downloads/ y activa el lanzador py.
  pause
  exit /b 1
)
py -3.13 -c "import sys; print(sys.version)"
if errorlevel 1 (
  echo No se encontro Python 3.13. Instala esa version y vuelve a ejecutar este archivo.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  py -3.13 -m venv .venv
  if errorlevel 1 goto :fallo
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :fallo
echo Instalacion terminada. Ejecuta INICIAR_MESSI.bat.
pause
exit /b 0
:fallo
echo La instalacion fallo. Conserva el mensaje de error para revisarlo.
pause
exit /b 1
