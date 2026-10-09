; Compile after building PySnips.spec (onedir) and PySnipsUpdater.spec (onefile).
; Keep this single version value in sync with data/system_data/version.json.
#define AppVersion "0.2.1"
git diff
[Setup]
; Permanent identity: never change this GUID for normal future releases.
AppId={{6A34FC85-F3CB-4544-9846-9F80D53853A9}
AppName=PySnips
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\PySnips
DefaultGroupName=PySnips
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableDirPage=no
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
Uninstallable=yes
UninstallDisplayIcon={app}\PySnips.exe
SetupIconFile=assets\icons\pysnips-multisize.ico
OutputDir=dist\installer
OutputBaseFilename=PySnips-{#AppVersion}-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
; Only application files are installed. LocalAppData\PySnips is never touched.
Source: "dist\PySnips\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\PySnipsUpdater.exe"; DestDir: "{app}"; Flags: ignoreversion
; Keep the public assets directory alongside both executables. Bundled Qt resource
; lookup still uses _internal/assets, and the ONEFILE updater embeds its own resources.
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\PySnips"; Filename: "{app}\PySnips.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\PySnips"; Filename: "{app}\PySnips.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\PySnips.exe"; Description: "Launch PySnips"; WorkingDir: "{app}"; Flags: postinstall nowait skipifsilent
