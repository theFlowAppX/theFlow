; theflow_setup.iss
; =========================================================
; Inno Setup script for theFlow! — Windows installer
; =========================================================
; Requirements:
;   1. Build the exe first:  python -m PyInstaller theflow.spec
;   2. Install Inno Setup:   https://jrsoftware.org/isdl.php
;   3. Run: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" theflow_setup.iss
; Output: dist\theFlow-0.1.0-setup.exe
; =========================================================

#define AppName      "theFlow!"
#define AppVersion   "0.1.0"
#define AppPublisher "Xavier Garès"
#define AppURL       "https://github.com/theFlowAppX/theFlow"
#define AppExeName   "theFlow.exe"
#define AppContact   "theflowapp@protonmail.com"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
AppContact={#AppContact}
DefaultDirName={autopf}\theFlow
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=theFlow-{#AppVersion}-setup
SetupIconFile=icons\logo.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExeName}
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";    Description: "{cm:CreateDesktopIcon}";    GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; Main executable
Source: "dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Documentation
Source: "documentation\theFlow_manual.html"; DestDir: "{app}\documentation"; Flags: ignoreversion

; Icons folder (contains logo.ico used for .flow file association)
Source: "icons\*"; DestDir: "{app}\icons"; Flags: ignoreversion recursesubdirs

; Logo files
Source: "logo\*"; DestDir: "{app}\logo"; Flags: ignoreversion recursesubdirs

[Icons]
; Start Menu shortcut
Name: "{group}\{#AppName}";          Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"

; Desktop shortcut (optional)
Name: "{autodesktop}\{#AppName}";    Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Dirs]
; Create settings folder so app can write settings.json
Name: "{app}\settings"

[Run]
; Offer to launch the app after install
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[Registry]
; ── Register .flow file extension ─────────────────────────────────────────────
; Associates .flow files with theFlow! so:
;   - Double-clicking opens the file in theFlow!
;   - Files show the theFlow! icon in Explorer
;   - The app receives the file path as sys.argv[1]

Root: HKA; Subkey: "Software\Classes\.flow"; \
    ValueType: string; ValueName: ""; ValueData: "theFlow.Document"; \
    Flags: uninsdeletevalue

Root: HKA; Subkey: "Software\Classes\theFlow.Document"; \
    ValueType: string; ValueName: ""; ValueData: "theFlow! Document"; \
    Flags: uninsdeletekey

; Icon for .flow files in Explorer — uses the app icon embedded in the exe
Root: HKA; Subkey: "Software\Classes\theFlow.Document\DefaultIcon"; \
    ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExeName},0"

; Open command — passes the file path as the first argument
Root: HKA; Subkey: "Software\Classes\theFlow.Document\shell\open\command"; \
    ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""

; Notify Windows Shell to refresh file associations
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.flow"; \
    ValueType: string; ValueName: "Application"; ValueData: "{#AppExeName}"; \
    Flags: uninsdeletekey

[UninstallDelete]
; Clean up settings on uninstall (comment out to keep user settings)
; Type: filesandordirs; Name: "{localappdata}\theFlow"
