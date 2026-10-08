param(
    [string]$Destination = (Join-Path ([Environment]::GetFolderPath('Desktop')) 'MESSI_Entregas_2_y_3'),
    [string]$PdfDirectory,
    [string]$ReleaseUrl = 'https://github.com/a3524110303-cpu/M.E.S.S.I-/releases/tag/v0.3.0-entregas',
    [string]$VideoUrl = 'https://github.com/a3524110303-cpu/M.E.S.S.I-/releases/download/v0.3.0-entregas/MESSI_Demo_Entrega_3.mp4'
)

$ErrorActionPreference = 'Stop'
$taskProjectRoot = Split-Path $PSScriptRoot -Parent
$taskDestination = [IO.Path]::GetFullPath($Destination)
$taskReleaseDirectory = Join-Path $taskProjectRoot 'release'
$taskFolders = @('Entrega_2', 'Entrega_3', 'Aplicacion', 'Codigo_y_evidencias', 'PDF')
foreach ($taskFolder in $taskFolders) {
    New-Item -ItemType Directory -Path (Join-Path $taskDestination $taskFolder) -Force | Out-Null
}

Copy-Item -LiteralPath (Join-Path $taskProjectRoot 'docs/entrega_2/02_Manual_del_programador.docx') -Destination (Join-Path $taskDestination 'Entrega_2') -Force
Copy-Item -LiteralPath (Join-Path $taskProjectRoot 'docs/entrega_2/03_Informe_de_pruebas_QA.docx') -Destination (Join-Path $taskDestination 'Entrega_2') -Force
Copy-Item -LiteralPath (Join-Path $taskProjectRoot 'docs/entrega_3/04_Manual_de_usuario.docx') -Destination (Join-Path $taskDestination 'Entrega_3') -Force
Copy-Item -LiteralPath (Join-Path $taskProjectRoot 'docs/entrega_3/05_Nota_de_prueba_con_persona_ajena.docx') -Destination (Join-Path $taskDestination 'Entrega_3') -Force
foreach ($taskName in @('MESSI_Demo_Entrega_3.mp4', 'MESSI_Demo_Entrega_3.srt')) {
    $taskSource = if ($taskName -like '*.mp4') { Join-Path $taskReleaseDirectory $taskName } else { Join-Path $taskProjectRoot "docs/entrega_3/$taskName" }
    Copy-Item -LiteralPath $taskSource -Destination (Join-Path $taskDestination 'Entrega_3') -Force
}
foreach ($taskName in @('MESSI-Setup-Windows-x64.exe', 'MESSI-Setup-Windows-x64.sha256')) {
    Copy-Item -LiteralPath (Join-Path $taskReleaseDirectory $taskName) -Destination (Join-Path $taskDestination 'Aplicacion') -Force
}
$taskPortableZip = Join-Path $taskReleaseDirectory 'MESSI-Portable-Windows-x64.zip'
if (Test-Path -LiteralPath $taskPortableZip) {
    Copy-Item -LiteralPath $taskPortableZip -Destination (Join-Path $taskDestination 'Aplicacion') -Force
}
Copy-Item -LiteralPath (Join-Path $taskProjectRoot 'installer/LEEME-cliente.txt') -Destination (Join-Path $taskDestination 'Aplicacion') -Force
Copy-Item -LiteralPath (Join-Path $taskProjectRoot 'docs/entrega_3/Verificacion_de_entregas_2_y_3.md') -Destination (Join-Path $taskDestination 'Codigo_y_evidencias') -Force
Copy-Item -LiteralPath (Join-Path $taskProjectRoot 'docs/entrega_2/Revision_Ismael_y_Victor_2026-10-08.md') -Destination (Join-Path $taskDestination 'Codigo_y_evidencias') -Force
Copy-Item -LiteralPath (Join-Path $taskProjectRoot 'docs/referencias/Examen_Parcial_1.pdf') -Destination (Join-Path $taskDestination 'Codigo_y_evidencias') -Force
Copy-Item -LiteralPath (Join-Path $taskProjectRoot 'data/synthetic/Plantilla_MESSI.xlsx') -Destination (Join-Path $taskDestination 'Aplicacion') -Force

if ($PdfDirectory) {
    foreach ($taskPdf in Get-ChildItem -LiteralPath $PdfDirectory -File -Filter '*.pdf') {
        Copy-Item -LiteralPath $taskPdf.FullName -Destination (Join-Path $taskDestination 'PDF') -Force
    }
}

# Git archive incluye únicamente archivos versionados, sin bases personales,
# credenciales, entornos Python ni intermediarios de construcción.
$taskSourceZip = Join-Path $taskDestination 'Codigo_y_evidencias/MESSI_Codigo_0.3.0.zip'
git -C $taskProjectRoot archive --format=zip --output=$taskSourceZip HEAD
if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el ZIP del código versionado.' }
$taskCommit = (git -C $taskProjectRoot rev-parse HEAD).Trim()

$taskReadme = @"
MESSI 0.3.0 - Entregas 2 y 3
Version del codigo: $taskCommit
Descargas publicas: $ReleaseUrl

Entrega_2: formatos 02 y 03 completos.
Entrega_3: manual 04, video de 4:25 y subtitulos.
IMPORTANTE: 05 es un protocolo PENDIENTE. El equipo confirmo que aun no hizo
la prueba con persona ajena. Victor debe observar sin intervenir y registrar
dificultades y cambios reales al manual; despues completar 05 en media pagina.
No presentar el formato pendiente como evidencia de una prueba realizada.

Aplicacion: abrir MESSI-Setup-Windows-x64.exe y seguir el asistente.
El cliente no necesita Python, MySQL ni internet durante el uso.
Para instalar en otra computadora basta con el instalador.
Portable: extrae el ZIP completo y abre MESSI/MESSI.exe, conservando _internal.
Windows 11 x64 probado; Windows 10 y segunda computadora no probados fisicamente.
Usar solo datos ficticios. Modelo sintetico; vistas de demostracion sin login.

Codigo_y_evidencias: codigo versionado y lista de cotejo. El ZIP incluye
dependencias fijadas, datos ficticios, scripts y evidencias tecnicas.
PDF: copias de lectura de los formatos; entregar los DOCX del maestro.

Pruebas actuales: 157 descubiertas, 150 aprobadas, 7 MySQL omitidas, 0 fallidas.
Instalacion actualizada y ejecutable comprobados sin Python en PATH;
la base del usuario se conservo. La desinstalacion aislada no se ejecuto.
Video: capturas reales y voz sintetica generica, no prueba con persona ajena.
"@
$taskReadme | Set-Content -LiteralPath (Join-Path $taskDestination 'LEEME_ENTREGA.txt') -Encoding utf8
"Video publico: $VideoUrl`nDescargas: $ReleaseUrl`nArchivo: MESSI_Demo_Entrega_3.mp4`n" | Set-Content -LiteralPath (Join-Path $taskDestination 'Entrega_3/Enlace_video.txt') -Encoding utf8

$taskManifest = foreach ($taskFile in Get-ChildItem -LiteralPath $taskDestination -Recurse -File | Where-Object Name -ne 'SHA256SUMS.txt' | Sort-Object FullName) {
    $taskRelative = [IO.Path]::GetRelativePath($taskDestination, $taskFile.FullName).Replace('\', '/')
    '{0}  {1}' -f (Get-FileHash -LiteralPath $taskFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant(), $taskRelative
}
$taskManifest | Set-Content -LiteralPath (Join-Path $taskDestination 'SHA256SUMS.txt') -Encoding utf8

$taskDocumentsZip = Join-Path $taskReleaseDirectory 'MESSI_Entregas_2_y_3.zip'
Compress-Archive -LiteralPath @(
    (Join-Path $taskDestination 'Entrega_2'),
    (Join-Path $taskDestination 'Entrega_3'),
    (Join-Path $taskDestination 'Codigo_y_evidencias'),
    (Join-Path $taskDestination 'PDF'),
    (Join-Path $taskDestination 'LEEME_ENTREGA.txt')
) -DestinationPath $taskDocumentsZip -Force
Write-Output "Entregables: $taskDestination"
Write-Output "ZIP de formatos, video y codigo: $taskDocumentsZip"
