param(
    [string]$BindAddress = '127.0.0.1',
    [ValidateRange(1024, 65535)][int]$Port = 8000
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot
$WebPython = Join-Path $ProjectRoot '.venv-web\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $WebPython)) { throw 'Primero ejecuta scripts\instalar_web.ps1.' }
& $WebPython web\manage.py check --database default
if ($LASTEXITCODE -ne 0) { throw 'Revisa web/.env y la conexión MySQL.' }
& $WebPython web\manage.py migrate --check
if ($LASTEXITCODE -ne 0) { throw 'Hay migraciones pendientes. Ejecuta web\manage.py migrate.' }
& $WebPython web\manage.py collectstatic --noinput
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron preparar los recursos estáticos.' }
Write-Host "MESSI web en http://${BindAddress}:$Port. Pulsa Ctrl+C para detenerlo."
Push-Location -LiteralPath (Join-Path $ProjectRoot 'web')
try {
    & $WebPython -m waitress --listen="${BindAddress}:$Port" --threads=4 config.wsgi:application
    if ($LASTEXITCODE -ne 0) { throw 'El servidor web finalizó con un error.' }
} finally {
    Pop-Location
}
