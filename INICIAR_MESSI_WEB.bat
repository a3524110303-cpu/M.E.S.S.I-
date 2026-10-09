@echo off
cd /d "%~dp0"
if exist ".qa\mysql-web\auto.cnf" (
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\iniciar_mysql_demo.ps1
    if errorlevel 1 exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\iniciar_web.ps1 -BindAddress 0.0.0.0 -Port 8000
if errorlevel 1 pause
