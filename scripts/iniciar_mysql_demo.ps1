param(
    [string]$MySqlBinary = 'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe'
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$SqlDataDir = [IO.Path]::GetFullPath((Join-Path $ProjectRoot '.qa\mysql-web'))
$WebPython = Join-Path $ProjectRoot '.venv-web\Scripts\python.exe'
$WebEnv = Join-Path $ProjectRoot 'web\.env'
if (-not (Test-Path -LiteralPath (Join-Path $SqlDataDir 'mysql')) -or -not (Test-Path -LiteralPath $WebEnv)) {
    throw 'No existe la instancia MySQL de ensayo configurada. Sigue docs/USO_WEB.md para preparar MySQL; este script no crea bases ni credenciales.'
}
if (-not (Test-Path -LiteralPath $WebPython) -or -not (Test-Path -LiteralPath $MySqlBinary)) {
    throw 'Se requiere .venv-web y el binario MySQL instalado. Usa -MySqlBinary si está en otra ruta.'
}
# Sólo lee host/puerto; no imprime ni incorpora las contraseñas en argumentos.
$DbAddress = @'
import os
import sys
from dotenv import load_dotenv
load_dotenv(sys.argv[1])
print(os.environ.get("MESSI_WEB_DB_HOST", ""))
print(os.environ.get("MESSI_WEB_DB_PORT", ""))
'@ | & $WebPython - $WebEnv
if ($LASTEXITCODE -ne 0 -or $DbAddress.Count -ne 2 -or $DbAddress[0] -ne '127.0.0.1' -or $DbAddress[1] -ne '33307') {
    throw 'Este script sólo administra el ensayo local configurado en 127.0.0.1:33307.'
}
$Listening = Get-NetTCPConnection -State Listen -LocalPort 33307 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($Listening) {
    $SqlProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($Listening.OwningProcess)"
    if (-not $SqlProcess -or [IO.Path]::GetFullPath($SqlProcess.ExecutablePath) -ne [IO.Path]::GetFullPath($MySqlBinary) -or $SqlProcess.CommandLine.IndexOf($SqlDataDir, [StringComparison]::OrdinalIgnoreCase) -lt 0) {
        throw 'El puerto 33307 está ocupado por otro proceso. No se modificó ni se detuvo.'
    }
    Write-Host 'La instancia MySQL de ensayo ya está disponible en 127.0.0.1:33307.'
    exit 0
}
$SqlLog = Join-Path $ProjectRoot '.qa\mysql-web.log'
$SqlArguments = @('--no-defaults', "--datadir=`"$SqlDataDir`"", '--port=33307', '--bind-address=127.0.0.1', '--mysqlx=0', "--log-error=`"$SqlLog`"")
$SqlStarted = Start-Process -FilePath $MySqlBinary -ArgumentList $SqlArguments -WindowStyle Hidden -PassThru
for ($Attempt = 0; $Attempt -lt 20; $Attempt++) {
    $SqlStarted.Refresh()
    if ($SqlStarted.HasExited) { throw 'MySQL de ensayo no pudo iniciar. Revisa .qa/mysql-web.log.' }
    if (Get-NetTCPConnection -State Listen -LocalPort 33307 -ErrorAction SilentlyContinue) {
        Write-Host 'Instancia MySQL de ensayo disponible en 127.0.0.1:33307. Usa scripts/iniciar_web.ps1 para el portal.'
        exit 0
    }
    Start-Sleep -Milliseconds 500
}
throw 'MySQL sigue iniciando. Revisa .qa/mysql-web.log y vuelve a comprobar la conexión.'
