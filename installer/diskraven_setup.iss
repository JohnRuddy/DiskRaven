; ───────────────────────────────────────────────────────────────────────────
;  DiskRaven — Inno Setup Installer Script
;  Creates a professional InstallShield-style wizard installer for Windows.
;
;  Prerequisites:
;    1.  Run  build.bat  first to produce  dist\DiskRaven\
;    2.  Install Inno Setup 6+  (https://jrsoftware.org/isinfo.php)
;
;  Build the installer:
;    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\diskraven_setup.iss
; ───────────────────────────────────────────────────────────────────────────

#define MyAppName        "DiskRaven"
#define MyAppVersion     "1.0.0"
#define MyAppPublisher   "DiskRaven Software"
#define MyAppURL         "https://diskraven.app"
#define MyAppExeName     "DiskRaven.exe"
#define MyAppDescription "See Everything. Reclaim Your Space."

[Setup]
; Unique GUID — regenerate if you fork the project
AppId={{B7E4C2A1-3F59-4D8B-9A12-7C6E8D5F0B3A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE.txt
InfoBeforeFile=..\installer\before_install.txt
OutputDir=..\dist\installer
OutputBaseFilename=DiskRaven_Setup_{#MyAppVersion}
SetupIconFile=..\diskmapper\assets\diskraven.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=110,110
WizardImageFile=..\diskmapper\assets\installer_wizard.bmp
WizardSmallImageFile=..\diskmapper\assets\installer_header.bmp
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
MinVersion=10.0
DisableProgramGroupPage=yes
DisableWelcomePage=no

; Branding colours (Inno Setup 6.1+)
; WizardImageBackColor=$1e1e2e      ; Catppuccin Base (not supported in modern style)

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";   Description: "{cm:CreateDesktopIcon}";  GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Create a &Quick Launch icon"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Include everything PyInstaller built
Source: "..\dist\DiskRaven\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Also include the license
Source: "..\LICENSE.txt";       DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}";            Filename: "{app}\{#MyAppExeName}"; Comment: "{#MyAppDescription}"
Name: "{group}\Uninstall {#MyAppName}";   Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";       Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "{#MyAppDescription}"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Registry]
; "Open with DiskRaven" context menu on drives (optional — admin only)
; Root: HKLM; Subkey: "Software\Classes\Drive\shell\DiskRaven"; ValueType: string; ValueName: ""; ValueData: "Scan with DiskRaven"; Flags: uninsdeletekey
; Root: HKLM; Subkey: "Software\Classes\Drive\shell\DiskRaven\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletekey

[UninstallDelete]
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\diskmapper"

[Code]
// Show custom "before install" info for first-time users
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
end;

procedure InitializeWizard;
begin
  // You could add custom wizard pages here for extra branding
  WizardForm.WelcomeLabel1.Caption := 'Welcome to DiskRaven';
  WizardForm.WelcomeLabel2.Caption :=
    'This wizard will install DiskRaven on your computer.'#13#10#13#10 +
    'DiskRaven is a high-performance disk visualization and cleanup tool ' +
    'that helps you see exactly where your space is going and reclaim it safely.'#13#10#13#10 +
    'Click Next to continue, or Cancel to exit.';
end;
