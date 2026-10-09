param()
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot
$WebPython = Join-Path $ProjectRoot '.venv-web\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $WebPython)) {
    & py -3.13 -m venv .venv-web
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear .venv-web. Instala Python 3.13 de 64 bits.' }
}
& $WebPython -m pip install -r requirements-web.txt
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias del portal.' }
$WebEnv = Join-Path $ProjectRoot 'web\.env'
if (-not (Test-Path -LiteralPath $WebEnv)) {
    $Config = Get-Content -LiteralPath (Join-Path $ProjectRoot 'web\.env.example') -Raw
    $Secret = & $WebPython -c 'import secrets; print(secrets.token_urlsafe(64))'
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo generar la clave del portal.' }
    $Config.Replace('CAMBIAR_CLAVE_ALEATORIA_DE_AL_MENOS_50_CARACTERES', $Secret.Trim()) | Set-Content -LiteralPath $WebEnv -Encoding utf8
}
if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot 'models\messi_demo.joblib'))) {
    & $WebPython scripts\train_demo.py
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el modelo sintético de demostración.' }
}
Write-Host 'Dependencias listas. Completa MySQL y los hosts en web/.env antes de continuar.'
Write-Host 'Después ejecuta: .\.venv-web\Scripts\python.exe web\manage.py migrate'
Write-Host 'Crea tu administrador: .\.venv-web\Scripts\python.exe web\manage.py createsuperuser'
Write-Host 'Consulta docs/USO_WEB.md para cuentas, asignaciones y publicación HTTPS.'
