#define AppVersion "0.4.0"

[Setup]
AppId={{7FB28D22-A856-4559-BCC3-32D9A44B2802}
AppName=MESSI
AppVersion={#AppVersion}
AppPublisher=Equipo MESSI
DefaultDirName={localappdata}\Programs\MESSI
DefaultGroupName=MESSI
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible and not arm64
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19041
OutputDir=..\release
OutputBaseFilename=MESSI-Setup-Windows-x64
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
CloseApplications=yes
UninstallDisplayIcon={app}\MESSI.exe
InfoBeforeFile=LEEME-cliente.txt

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "..\dist\MESSI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\MESSI"; Filename: "{app}\MESSI.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\MESSI"; Filename: "{app}\MESSI.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\MESSI.exe"; Description: "Abrir MESSI"; Flags: nowait postinstall skipifsilent

; Los datos en {localappdata}\MESSI se conservan al actualizar/desinstalar.
