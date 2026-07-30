; =============================================================================
; Tool Pouch v3 — Inno Setup installer script
; =============================================================================
; Spec §7: "Wrap the PyInstaller output in a real installer (Inno Setup
; recommended — free, scriptable, well-documented, simpler to author
; than WiX for a single-exe Python app) instead of shipping a dist/
; folder to unzip. Installer writes to %APPDATA%\ToolPouch\config.json
; on first run and creates a Start Menu entry, same as any normal
; Windows app install."
;
; Build with:
;     ISCC.exe installer\toolpouch.iss
;
; Prerequisites:
;     - PyInstaller build already produced in dist\ToolPouch\
;       (run ``build.bat`` first)
;     - Optional: a minimal embeddable Python under
;       installer\python-embed\python.exe — this is the FALLBACK
;       interpreter for .py tool scripts when no system Python is on
;       PATH. If absent, .py tools require a system Python install.
; =============================================================================

#define MyAppName          "Tool Pouch"
; Version passed from CI via /dMY_APP_VERSION=... or defaults to 3.0.0
#ifndef MyAppVersion
#define MyAppVersion       "3.0.0"
#endif
#define MyAppPublisher     "ToolPouch"
#define MyAppExeName       "ToolPouch.exe"
#define MyAppSourceDir     "..\dist\ToolPouch"
#define MyPythonEmbedDir   "python-embed"

[Setup]
AppId={{8F4E6B7A-3C2D-4E1A-9B5F-7D8E9F0A1B2C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=ToolPouch-Setup-{#MyAppVersion}
; Compression: lzma2/normal is ~5× faster to build than lzma2/ultra64
; with only ~5% larger output. The previous ultra64 + SolidCompression
; combo caused multi-minute build times on slower machines. Solid
; compression also slows random access during install.
Compression=lzma2/normal
SolidCompression=no
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; PrivilegesRequired=lowest + {autopf} installs to
; %LOCALAPPDATA%\Programs\Tool Pouch (user-writable, NO admin needed).
; The app seeds tools to ~/.toolpouch/ (also user-writable) on first
; launch. Both locations must be user-writable — if the user overrides
; and installs to C:\Program Files\, the app will crash with
; PermissionError on first launch because it can't write there.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; The entire PyInstaller onedir output (the .exe + the _internal/ folder
; with all bundled Python + DLLs).
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Optional: ship a minimal embeddable Python as a fallback for .py tool
; scripts (spec §4 + §7). This is a SEPARATE, deliberately-minimal
; Python — NOT the one bundled by PyInstaller for the UI. Place its
; contents under installer/python-embed/ before building.
Source: "{#MyPythonEmbedDir}\*"; DestDir: "{app}\python-embed"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: DirExists(ExpandConstant('{#MyPythonEmbedDir}'))

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; ==========================================================================
; File association: .toolpouch extension
; ==========================================================================
; Registers .toolpouch files so double-clicking them opens Tool Pouch,
; which auto-imports the tool and selects it.
;
; HKCR (HKEY_CLASSES_ROOT) is the union of HKLM\Software\Classes and
; HKCU\Software\Classes. With PrivilegesRequired=lowest we write to
; HKCU (per-user, no admin needed). Inno Setup's HKCR root automatically
; routes to HKCU when PrivilegesRequired=lowest.
[Registry]
; Register the .toolpouch extension
Root: HKCR; Subkey: ".toolpouch"; ValueType: string; ValueName: ""; ValueData: "ToolPouch.ToolPackage"; Flags: uninsdeletevalue
; Register the file type description
Root: HKCR; Subkey: "ToolPouch.ToolPackage"; ValueType: string; ValueName: ""; ValueData: "Tool Pouch Package"; Flags: uninsdeletekey
; Set the icon for .toolpouch files (uses the app's icon)
Root: HKCR; Subkey: "ToolPouch.ToolPackage\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Flags: uninsdeletekey
; Register the "open" verb: double-click → ToolPouch.exe "%1"
Root: HKCR; Subkey: "ToolPouch.ToolPackage\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletekey

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Inno Setup's default uninstall already removes everything it installed
; (tracked via the install log). These entries are belt-and-suspenders
; for the bundled tools/assets that live under _internal/.
; DELIBERATELY do NOT remove %USERPROFILE%\.toolpouch (config.json +
; logs + user tools) — the user might reinstall and want their
; settings/tools back. They can delete that folder manually for a full clean.
Type: filesandordirs; Name: "{app}\_internal\tools"
Type: filesandordirs; Name: "{app}\_internal\assets"
Type: dirifempty; Name: "{app}"

; NOTE: No [Code] section needed. The previous version had a custom
; ``DirExists`` function here that called itself recursively — an
; infinite loop that caused the installer to hang forever on
; "Preparing to install". Inno Setup has a BUILT-IN ``DirExists``
; function; defining your own with the same name shadows it and recurses.
; Removed entirely.
