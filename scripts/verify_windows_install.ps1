<#
Verifica el instalador en una carpeta QA nueva. Si MESSI ya está instalado,
aborta antes de cambiar la instalación, el registro o los datos del usuario.
Requiere Python sólo para preparar/comprobar registros ficticios de prueba;
el ejecutable instalado se verifica con un PATH que no contiene Python.
#>
param([string]$Setup = '', [string]$Python = '')
$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$taskQa = Join-Path $taskRoot '.qa'
$taskEvidence = Join-Path $taskRoot 'docs\entrega_2\evidencias'
$taskRelease = Join-Path $taskRoot 'release'
$taskReport = [ordered]@{
    version_objetivo = '0.3.0'
    fecha = (Get-Date).ToString('o')
    plataforma = [Environment]::OSVersion.VersionString
    tipo = 'Instalacion, reinstalacion y desinstalacion en carpeta aislada'
    estado = 'pendiente'
    ok = $false
    errores = @()
}
$taskKeyName = '{7FB28D22-A856-4559-BCC3-32D9A44B2802}_is1'
$taskRegistryPaths = @(
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$taskKeyName",
    "HKCU:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\$taskKeyName",
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$taskKeyName",
    "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\$taskKeyName"
)
function Get-TaskInstallation {
    foreach ($taskKey in $taskRegistryPaths) {
        if (Test-Path -LiteralPath $taskKey) {
            Get-ItemProperty -LiteralPath $taskKey
        }
    }
}
function Save-TaskReport {
    New-Item -ItemType Directory -Path $taskEvidence -Force | Out-Null
    New-Item -ItemType Directory -Path $taskRelease -Force | Out-Null
    $taskJson = $taskReport | ConvertTo-Json -Depth 12
    $taskJson | Set-Content -LiteralPath (Join-Path $taskEvidence 'verificacion_instalador.json') -Encoding UTF8
    $taskJson | Set-Content -LiteralPath (Join-Path $taskRelease 'verificacion-instalacion.json') -Encoding UTF8
}
function Assert-TaskContainedPath([string]$Candidate, [string]$Parent) {
    $taskCandidate = [IO.Path]::GetFullPath($Candidate)
    $taskPrefix = [IO.Path]::GetFullPath($Parent).TrimEnd('\') + '\'
    if (-not $taskCandidate.StartsWith($taskPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'La ruta de comprobacion no pertenece a la carpeta autorizada.'
    }
    if (Test-Path -LiteralPath $Parent) {
        $taskParentItem = Get-Item -LiteralPath $Parent
        if ($taskParentItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw 'La carpeta autorizada no debe ser un enlace o punto de reanalisis.'
        }
    }
    if (Test-Path -LiteralPath $taskCandidate) {
        $taskItem = Get-Item -LiteralPath $taskCandidate
        if ($taskItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw 'La comprobacion no admite enlaces o puntos de reanalisis.'
        }
    }
}
function Start-TaskProcess([string]$File, [string[]]$Arguments) {
    $taskProcess = Start-Process -FilePath $File -ArgumentList $Arguments -WorkingDirectory $env:TEMP -WindowStyle Hidden -Wait -PassThru
    if ($taskProcess.ExitCode -ne 0) { throw "El proceso de comprobacion termino con codigo $($taskProcess.ExitCode)." }
    return $taskProcess.ExitCode
}

# Esta guardia se ejecuta antes de crear la carpeta QA o invocar el instalador.
$taskExisting = @(Get-TaskInstallation)
if ($taskExisting.Count -gt 0) {
    $taskReport.estado = 'omitida'
    $taskReport.instalacion_existente_detectada = $true
    $taskReport.version_existente = $taskExisting[0].DisplayVersion
    $taskReport.motivo = 'Existe una instalacion MESSI. No se modificaron aplicacion, registro ni datos del usuario.'
    Save-TaskReport
    Write-Output $taskReport.motivo
    exit 2
}
# Proteger tambien un acceso directo previo que no tenga registro asociado.
$taskShortcut = Join-Path ([Environment]::GetFolderPath('Programs')) 'MESSI.lnk'
if (Test-Path -LiteralPath $taskShortcut) {
    $taskReport.estado = 'omitida'
    $taskReport.motivo = 'Existe un acceso directo MESSI previo. No se modifico.'
    Save-TaskReport
    Write-Output $taskReport.motivo
    exit 2
}
if (-not $Setup) { $Setup = Join-Path $taskRelease 'MESSI-Setup-Windows-x64.exe' }
if (-not $Python) { $Python = Join-Path $taskRoot '.venv\Scripts\python.exe' }
if (-not (Test-Path -LiteralPath $Setup)) { throw 'No se encontro el instalador.' }
if (-not (Test-Path -LiteralPath $Python)) { throw 'No se encontro Python para preparar la fixture ficticia.' }
$taskSetup = (Resolve-Path -LiteralPath $Setup).Path
$taskPython = (Resolve-Path -LiteralPath $Python).Path
$taskRun = Join-Path $taskQa ('instalador-' + [guid]::NewGuid().ToString('N'))
Assert-TaskContainedPath $taskRun $taskQa
if (Test-Path -LiteralPath $taskRun) { throw 'La carpeta nueva de comprobacion ya existe.' }
New-Item -ItemType Directory -Path $taskRun | Out-Null
$taskInstall = Join-Path $taskRun 'aplicacion'
$taskData = Join-Path $taskRun 'datos-ficticios'
$taskFixture = Join-Path $taskRun 'fixture.py'
$taskOldPath = $env:PATH
$taskOldData = $env:MESSI_DATA_DIR
$taskInstalled = $false
@'
import json
import sys
sys.path.insert(0, sys.argv[1])
from messi.paths import database_path
from messi.sqlite_storage import SQLiteStore
store = SQLiteStore(database_path())
if sys.argv[2] == 'seed':
    store.save_indicators([dict(id_estudiante='EST-777', nota_parcial=6.0, asistencia=80.0, tareas_entregadas=70.0)])
    store.create_request('EST-777', 'Registro ficticio para verificar conservacion')
assert len(store.list_requests('EST-777')) == 1
assert store.list_indicators()[0]['id_estudiante'] == 'EST-777'
print(json.dumps({'solicitudes_ficticias': 1, 'indicadores_ficticios': 1}))
'@ | Set-Content -LiteralPath $taskFixture -Encoding UTF8
try {
    $env:MESSI_DATA_DIR = $taskData
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    $taskReport.sha256_instalador = (Get-FileHash -LiteralPath $taskSetup -Algorithm SHA256).Hash
    $taskReport.sin_python_en_path = $true
    $taskReport.datos = 'Registros ficticios aislados; no usa la base del usuario.'
    $taskInstallArguments = @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/NOICONS','/TASKS=',('/DIR="' + $taskInstall + '"'),('/LOG="' + (Join-Path $taskRun 'instalacion.log') + '"'))
    $taskReport.instalacion_exit = Start-TaskProcess $taskSetup $taskInstallArguments
    $taskInstalled = $true
    $taskRegistered = @(Get-TaskInstallation)
    if ($taskRegistered.Count -ne 1 -or [IO.Path]::GetFullPath($taskRegistered[0].InstallLocation).TrimEnd('\') -ne $taskInstall) {
        throw 'El registro no corresponde a la carpeta aislada; se suspende la comprobacion.'
    }
    $taskReport.version_instalada = $taskRegistered[0].DisplayVersion
    if ($taskReport.version_instalada -ne $taskReport.version_objetivo) { throw 'La version instalada es distinta de la esperada.' }
    $taskExe = Join-Path $taskInstall 'MESSI.exe'
    Assert-TaskContainedPath $taskExe $taskRun
    foreach ($taskMode in @('--self-test','--smoke-server')) {
        $taskOutput = Join-Path $taskRun ($taskMode.TrimStart('-') + '.json')
        [void](Start-TaskProcess $taskExe @($taskMode,'--salida',('"' + $taskOutput + '"')))
        $taskResult = Get-Content -LiteralPath $taskOutput -Raw -Encoding UTF8 | ConvertFrom-Json
        if (-not $taskResult.ok) { throw "Fallo la verificacion $taskMode." }
        $taskReport[$taskMode.TrimStart('-')] = $taskResult
    }
    & $taskPython $taskFixture (Join-Path $taskRoot 'src') seed
    if ($LASTEXITCODE -ne 0) { throw 'Fallo la fixture ficticia.' }
    $taskReport.reinstalacion_exit = Start-TaskProcess $taskSetup $taskInstallArguments
    & $taskPython $taskFixture (Join-Path $taskRoot 'src') check
    if ($LASTEXITCODE -ne 0) { throw 'La reinstalacion no conservo los registros.' }
    $taskReport.reinstalacion_conserva_datos = $true
    $taskUninstaller = Join-Path $taskInstall 'unins000.exe'
    Assert-TaskContainedPath $taskUninstaller $taskRun
    $taskReport.desinstalacion_exit = Start-TaskProcess $taskUninstaller @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART')
    $taskInstalled = $false
    & $taskPython $taskFixture (Join-Path $taskRoot 'src') check
    if ($LASTEXITCODE -ne 0) { throw 'La desinstalacion no conservo los registros.' }
    if (Test-Path -LiteralPath $taskExe) { throw 'La aplicacion de prueba sigue instalada.' }
    if (@(Get-TaskInstallation).Count -ne 0) { throw 'Quedo el registro de la instalacion de prueba.' }
    $taskReport.desinstalacion_conserva_datos = $true
    $taskReport.estado = 'completada'
    $taskReport.ok = $true
} catch {
    $taskReport.estado = 'fallida'
    $taskReport.errores += $_.Exception.Message
} finally {
    # Ante un fallo, limpiar solo si el registro sigue apuntando a esta prueba.
    if ($taskInstalled) {
        $taskRegistered = @(Get-TaskInstallation)
        if ($taskRegistered.Count -eq 1 -and [IO.Path]::GetFullPath($taskRegistered[0].InstallLocation).TrimEnd('\') -eq $taskInstall) {
            $taskUninstaller = Join-Path $taskInstall 'unins000.exe'
            if (Test-Path -LiteralPath $taskUninstaller) {
                try {
                    Assert-TaskContainedPath $taskUninstaller $taskRun
                    [void](Start-TaskProcess $taskUninstaller @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART'))
                    $taskReport.limpieza_instalacion_prueba = $true
                } catch { $taskReport.errores += 'La instalacion aislada requiere revision manual.' }
            }
        }
    }
    $env:PATH = $taskOldPath
    if ($null -eq $taskOldData) { Remove-Item Env:MESSI_DATA_DIR -ErrorAction SilentlyContinue }
    else { $env:MESSI_DATA_DIR = $taskOldData }
    # Se conservan la carpeta QA y sus logs/fixtures para revisar evidencia.
    Save-TaskReport
}
$taskReport | ConvertTo-Json -Depth 12
if (-not $taskReport.ok) { exit 1 }
