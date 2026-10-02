; =====================================================================
;  Playa - Inno Setup installer script
;  Builds Setup\Playa-Setup.exe which installs the app and creates a
;  Desktop shortcut (and Start Menu entry) automatically.
;
;  How to use:
;   1) First run build.bat  (creates dist\Playa\ with Playa.exe).
;   2) Install Inno Setup (free): https://jrsoftware.org/isdl.php
;   3) Open this file in Inno Setup and press Compile (or run:
;        iscc installer\playa.iss   ).
;   The finished installer appears in  installer\Setup\Playa-Setup.exe
; =====================================================================

#define MyAppName "Playa"
#define MyAppVersion "1.4.3"
#define MyAppExeName "Playa.exe"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=Setup
OutputBaseFilename=Playa-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; 64-bit install
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=..\assets\playa.ico

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checkedonce

[Files]
; Take the whole PyInstaller output folder
Source: "..\dist\Playa\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}";        Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";  Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
