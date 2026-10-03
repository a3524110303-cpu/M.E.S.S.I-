@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Primero ejecuta INSTALAR_MESSI.bat.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m unittest discover -s tests -v
set "messiTestExit=%ERRORLEVEL%"
pause
exit /b %messiTestExit%
