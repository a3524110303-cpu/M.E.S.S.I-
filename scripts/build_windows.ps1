param([string]$Python = '', [string]$ISCC = '', [switch]$SoloPortable)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    if (-not $Python) {
        $Python = (& py -3.13 -c 'import sys; print(sys.executable)').Trim()
        if ($LASTEXITCODE -ne 0) { throw 'Instala Python 3.13 x64 en la computadora de construcción.' }
    }
    & $Python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'No pude crear el entorno privado.' }
}
$taskPy = Join-Path $taskRoot '.venv\Scripts\python.exe'
& $taskPy -c "import struct,sys; assert struct.calcsize('P')==8 and (3,11)<=sys.version_info[:2]<(3,14), 'Se necesita Python 3.11-3.13 x64'"
if ($LASTEXITCODE -ne 0) { throw 'Python incompatible para este paquete.' }
& $taskPy -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Fallaron las dependencias de construcción.' }
& $taskPy -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Las dependencias tienen un conflicto.' }
& $taskPy scripts\train_demo.py
if ($LASTEXITCODE -ne 0) { throw 'Falló el entrenamiento local.' }
& $taskPy -m unittest discover -s tests -q
if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas.' }
& $taskPy -m PyInstaller --noconfirm MESSI.spec
if ($LASTEXITCODE -ne 0) { throw 'Falló el empaquetado.' }
Copy-Item -LiteralPath 'installer\LEEME-cliente.txt' -Destination 'dist\MESSI\LEEME.txt' -Force
Copy-Item -LiteralPath 'installer\TERCEROS.md' -Destination 'dist\MESSI\TERCEROS.md' -Force
New-Item -ItemType Directory -Path 'release' -Force | Out-Null
$taskOldData = $env:MESSI_DATA_DIR
$taskOldPath = $env:PATH
try {
    $env:MESSI_DATA_DIR = Join-Path $taskRoot 'build\prueba-paquete'
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    $taskExe = Join-Path $taskRoot 'dist\MESSI\MESSI.exe'
    foreach ($taskMode in @('--self-test','--smoke-server')) {
        $taskReport = Join-Path $taskRoot ('release\verificacion-' + $taskMode.TrimStart('-') + '.json')
        $taskProcess = Start-Process -FilePath $taskExe -ArgumentList @($taskMode,'--salida',('"' + $taskReport + '"')) -WorkingDirectory $env:TEMP -WindowStyle Hidden -Wait -PassThru
        if ($taskProcess.ExitCode -ne 0) { throw "Falló la comprobación del ejecutable. Revisa $taskReport" }
    }
} finally {
    $env:PATH = $taskOldPath
    if ($null -eq $taskOldData) { Remove-Item Env:MESSI_DATA_DIR -ErrorAction SilentlyContinue }
    else { $env:MESSI_DATA_DIR = $taskOldData }
}
if (-not $SoloPortable) {
    if (-not $ISCC) {
        $taskCompiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
        $ISCC = if ($taskCompiler) { $taskCompiler.Source } else { Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe' }
    }
    if (-not (Test-Path -LiteralPath $ISCC)) { throw 'Instala Inno Setup 6 o pasa -ISCC con la ruta de ISCC.exe.' }
    & $ISCC /Q installer\MESSI.iss
    if ($LASTEXITCODE -ne 0) { throw 'Falló la creación del instalador.' }
    $taskHash = Get-FileHash -LiteralPath 'release\MESSI-Setup-Windows-x64.exe' -Algorithm SHA256
    ($taskHash.Hash + '  MESSI-Setup-Windows-x64.exe') | Set-Content -LiteralPath 'release\MESSI-Setup-Windows-x64.sha256' -Encoding ascii
}
Write-Output 'Listo: release\MESSI-Setup-Windows-x64.exe. Para portable, copia toda la carpeta dist\MESSI.'
