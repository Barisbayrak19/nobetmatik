; Inno Setup 6 Script - NöbetMatik Okul Nöbet Yönetim Sistemi
#define MyAppName "NöbetMatik"
#define MyAppVersion "2.0.2"
#define MyAppPublisher "Barış Bayrak"
#define MyAppURL "https://github.com/Barisbayrak19/nobetmatik"
#define MyAppExeName "NobetMatik.exe"

[Setup]
AppId={{9B78D8D3-E625-42E1-91CE-FE8120B4CD8A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=NobetMatik_v{#MyAppVersion}_Kurulum
SetupIconFile=..\assets\app_icon.ico
UninstallDisplayIcon={app}\assets\app_icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
WizardResizable=no
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Dirs]
Name: "{app}\data"
Name: "{app}\logs"
Name: "{app}\backups"
Name: "{app}\exports"

[Files]
Source: "..\dist\NobetMatik\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\NobetMatik\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "{#MyAppExeName},data\nobet.db,data\nobet.db-journal,*.log"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Kaldırma işleminde sadece geçici log ve önbellekleri sil, okulun veritabanına ve yedeklerine asla dokunma!
Type: files; Name: "{app}\logs\*.log"
Type: files; Name: "{app}\data\announcements_cache.json"
