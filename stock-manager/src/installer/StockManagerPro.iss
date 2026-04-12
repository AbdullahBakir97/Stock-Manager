; ============================================================
;  Stock Manager Pro — Inno Setup 7 Installer Script
;  Version : 2.3.0
;  Requires: Inno Setup 7  (https://jrsoftware.org/isdl.php)
;
;  HOW TO BUILD:
;    1. PyInstaller first (from repo root):
;         cd src
;         pyinstaller StockManagerPro.spec --noconfirm --clean
;    2. Compile installer:
;         iscc installer\StockManagerPro.iss
;    Output → installer\Output\StockManagerPro-2.3.0-setup.exe
;
;  Or just run:  installer\build_installer.bat
; ============================================================

#define AppName      "Stock Manager Pro"
#ifndef AppVersion
  #define AppVersion "2.3.4"
#endif
#define AppPublisher "StockPro Software"
#define AppURL       "https://github.com/AbdullahBakir97/Stock-Manager"
#define AppExeName   "StockManagerPro.exe"
#define AppDataDir   "{localappdata}\StockPro\StockManagerPro"

; PyInstaller COLLECT output — relative to this .iss file (installer\ folder)
#define SrcDir       "..\dist\StockManagerPro"

; ── App GUID — NEVER change this; it links upgrades together ─────────────────
#define AppId        "{{A7C2E591-4F3D-4B8A-9D1E-3F6B82A0C45D}"

; ─────────────────────────────────────────────────────────────────────────────
[Setup]
AppId                    = {#AppId}
AppName                  = {#AppName}
AppVersion               = {#AppVersion}
AppVerName               = {#AppName} {#AppVersion}
AppPublisher             = {#AppPublisher}
AppPublisherURL          = {#AppURL}
AppSupportURL            = {#AppURL}/issues
AppUpdatesURL            = {#AppURL}/releases

DefaultDirName           = {autopf}\{#AppName}
DefaultGroupName         = {#AppName}
DisableProgramGroupPage  = yes

; Output
OutputDir                = Output
OutputBaseFilename       = StockManagerPro-{#AppVersion}-setup
SetupIconFile            = ..\files\img\icon_cube.ico
UninstallDisplayIcon     = {app}\{#AppExeName}
UninstallDisplayName     = {#AppName} {#AppVersion}

; Compression (Inno Setup 7 supports lzma2)
Compression              = lzma2/ultra64
SolidCompression         = yes
LZMAUseSeparateProcess   = yes

; Wizard appearance (Inno Setup 7 modern style)
WizardStyle              = modern
WizardResizable          = no
WizardImageFile          = assets\wizard_banner.bmp
WizardSmallImageFile     = assets\wizard_icon.bmp

; Windows 10 1809+ required
MinVersion               = 10.0.17763

; 64-bit only
ArchitecturesInstallIn64BitMode = x64compatible
ArchitecturesAllowed            = x64compatible

; Run as current user (no UAC prompt unless installing to Program Files)
PrivilegesRequired                  = lowest
PrivilegesRequiredOverridesAllowed  = commandline dialog

; Close running instance before installing
CloseApplications        = yes
CloseApplicationsFilter  = {#AppExeName}
RestartApplications      = yes

; Misc
CreateUninstallRegKey    = yes
Uninstallable            = yes
ChangesAssociations      = no

; ── Signing (uncomment + fill once you have a code-signing cert) ──────────────
; SignTool     = signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /f "%CERT_PATH%" /p "%CERT_PASS%" $f
; SignedUninstaller = yes

; ─────────────────────────────────────────────────────────────────────────────
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german";  MessagesFile: "compiler:Languages\German.isl"

; ─────────────────────────────────────────────────────────────────────────────
[CustomMessages]
english.CreateDesktopIcon=Create a &desktop shortcut
german.CreateDesktopIcon=&Desktop-Verknüpfung erstellen
english.LaunchAfterInstall=&Launch {#AppName} now
german.LaunchAfterInstall={#AppName} &jetzt starten

; ─────────────────────────────────────────────────────────────────────────────
[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

; ─────────────────────────────────────────────────────────────────────────────
[Dirs]
; User-data folders — survive uninstall (no Flags: deleteafterinstall)
Name: "{#AppDataDir}";         Permissions: everyone-full
Name: "{#AppDataDir}\backups"; Permissions: everyone-full
Name: "{#AppDataDir}\logs";    Permissions: everyone-full

; ─────────────────────────────────────────────────────────────────────────────
[Files]
; Main application bundle from PyInstaller
Source: "{#SrcDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; ─────────────────────────────────────────────────────────────────────────────
[Icons]
; Start Menu
; PyInstaller 6.x stores data files in {app}\_internal\, not {app}\ directly.
; The EXE has the icon embedded — omit IconFilename so Windows reads it from the EXE.
Name: "{group}\{#AppName}";           Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
; Desktop (optional)
Name: "{autodesktop}\{#AppName}";     Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

; ─────────────────────────────────────────────────────────────────────────────
[Registry]
; Store install info for the built-in update checker
Root: HKCU; Subkey: "Software\StockPro\StockManagerPro"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}";          Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\StockPro\StockManagerPro"; ValueType: string; ValueName: "Version";     ValueData: "{#AppVersion}"

; ─────────────────────────────────────────────────────────────────────────────
[Run]
; Optional "launch now" checkbox on the Finish page
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchAfterInstall}"; Flags: nowait postinstall skipifsilent

; ─────────────────────────────────────────────────────────────────────────────
[UninstallRun]
; Gracefully kill the app before files are removed
Filename: "taskkill.exe"; Parameters: "/f /im {#AppExeName}"; Flags: skipifdoesntexist runhidden waituntilterminated

; ─────────────────────────────────────────────────────────────────────────────
[UninstallDelete]
; Remove app install folder — user data in %LOCALAPPDATA% is intentionally left intact
Type: filesandordirs; Name: "{app}"

; ─────────────────────────────────────────────────────────────────────────────
[Code]

{ ── Detect existing installation for upgrade flow ─────────────────────────── }
function GetUninstallString(): String;
var
  sKey, sVal: String;
begin
  sKey := ExpandConstant('Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1');
  sVal := '';
  if not RegQueryStringValue(HKCU, sKey, 'UninstallString', sVal) then
    RegQueryStringValue(HKLM, sKey, 'UninstallString', sVal);
  Result := sVal;
end;

function IsUpgrade(): Boolean;
begin
  Result := (GetUninstallString() <> '');
end;

function SilentUninstallPrevious(): Integer;
var
  sUninstall: String;
  iCode: Integer;
begin
  Result := 0;
  sUninstall := RemoveQuotes(GetUninstallString());
  if sUninstall <> '' then
    if Exec(sUninstall, '/SILENT /NORESTART /SUPPRESSMSGBOXES', '', SW_HIDE, ewWaitUntilTerminated, iCode) then
      Result := iCode
    else
      Result := 1;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
    if IsUpgrade() then
      SilentUninstallPrevious();
end;

{ ── Ready memo: show upgrade notice if applicable ──────────────────────────── }
function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo,
  MemoTypeInfo, MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
var
  s: String;
begin
  s := '';
  if IsUpgrade() then
    s := 'Upgrading existing installation of {#AppName}.' + NewLine + NewLine;
  s := s + MemoDirInfo;
  if MemoTasksInfo <> '' then
    s := s + NewLine + NewLine + MemoTasksInfo;
  Result := s;
end;
