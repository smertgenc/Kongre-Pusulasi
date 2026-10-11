#ifndef AppVersion
  #error AppVersion must be supplied by build_windows.py
#endif
#ifndef Publisher
  #error Publisher must be supplied by IT / the release owner
#endif
#ifndef SourceDir
  #error SourceDir is required
#endif
#ifndef ReleaseDir
  #error ReleaseDir is required
#endif

[Setup]
AppId={{A87A5B8D-9739-4927-B5C8-F09E5D96560E}
AppName=AHP Congress Analyzer
AppVersion={#AppVersion}
AppPublisher={#Publisher}
VersionInfoVersion={#AppVersion}.0
VersionInfoDescription=AHP-Based Conference Analysis and Decision Support System
DefaultDirName={autopf}\AHP Congress Analyzer
DefaultGroupName=AHP Congress Analyzer
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible and not arm64
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir={#ReleaseDir}
OutputBaseFilename=AHP-Congress-Analyzer-Setup-{#AppVersion}
SetupIconFile=app.ico
UninstallDisplayIcon={app}\AHP-Congress-Analyzer.exe
UninstallDisplayName=AHP Congress Analyzer
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
AppMutex=Local\AHP-Congress-Analyzer
CloseApplications=no
RestartApplications=no
SetupLogging=yes
#ifdef SignCommand
SignTool=approved
SignedUninstaller=yes
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; Remove obsolete bundled libraries on upgrade. This is application code, never user data.
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{group}\AHP Congress Analyzer"; Filename: "{app}\AHP-Congress-Analyzer.exe"; WorkingDir: "{app}"
Name: "{group}\Veritabanını yedekle"; Filename: "{app}\AHP-Congress-Analyzer.exe"; Parameters: "--backup"; WorkingDir: "{app}"
Name: "{autodesktop}\AHP Congress Analyzer"; Filename: "{app}\AHP-Congress-Analyzer.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\AHP-Congress-Analyzer.exe"; Description: "AHP Congress Analyzer uygulamasını aç"; Flags: nowait postinstall skipifsilent runasoriginaluser

; User data and Generic Credentials are deliberately outside the installer scope.
; No UninstallDelete, service, scheduled task, firewall or startup entries.
[Code]
function HasWebView2: Boolean;
var Value: String;
    Key: String;
begin
  Key := 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  Result := (RegQueryStringValue(HKLM32, Key, 'pv', Value) and (Value <> '') and (Value <> '0.0.0.0')) or
            (RegQueryStringValue(HKLM64, Key, 'pv', Value) and (Value <> '') and (Value <> '0.0.0.0'));
end;

function InitializeSetup: Boolean;
var DotNet: Cardinal;
begin
  Result := False;
  if not HasWebView2 then begin
    MsgBox('Microsoft Edge WebView2 Evergreen x64 Runtime gerekli. BT biriminiz Runtime paketini bilgisayar genelinde kurmalıdır. Kurulum otomatik indirme veya güvenlik ayarı değişikliği yapmaz.', mbError, MB_OK);
    Exit;
  end;
  if (not RegQueryDWordValue(HKLM32, 'SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full', 'Release', DotNet)) or (DotNet < 394802) then begin
    MsgBox('Microsoft .NET Framework 4.6.2 veya sonrası gerekli. BT biriminize danışın.', mbError, MB_OK);
    Exit;
  end;
  Result := True;
end;
