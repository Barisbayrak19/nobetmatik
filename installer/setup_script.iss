; Inno Setup 6 Script - NöbetMatik Okul Nöbet ve Ders Dağıtım Sistemi
#define MyAppName "NöbetMatik"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "Nöbet Yönetim Sistemleri"
#define MyAppExeName "NobetMatik.exe"

[Setup]
AppId={{9B78D8D3-E625-42E1-91CE-FE8120B4CD8A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=NobetMatik_Kurulum_v2.0.0
SetupIconFile=..\assets\app_icon.ico
UninstallDisplayIcon={app}\assets\app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\NobetMatik\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\NobetMatik\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Okul veritabanı koruması: Güncelleme kurulsa dahi okulun mevcut nöbet ve ders verisi asla silinmez!
Source: "..\dist\NobetMatik\data\nobet.db"; DestDir: "{app}\data"; Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
