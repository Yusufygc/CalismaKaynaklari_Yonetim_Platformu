#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

#define MyAppName "Kaynak Yönetim Platformu"
#define MyAppExeName "KaynakYonetimPlatformu.exe"
#define MyAppPublisher "Yusufygc"

[Setup]
; SABİT AppId: Sonraki sürümlerin uygulamanın üstüne doğru yazması için değiştirilmez.
AppId={{7470CA3F-5001-4DFC-BFF7-5535C9C85DAD}}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppPublisher={#MyAppPublisher}
; lowest: UAC sormaz, %LOCALAPPDATA%\Programs altına kurar. Uygulama içi güncelleme sessizce çalışır.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={autopf}\KaynakYonetimPlatformu
DefaultGroupName={#MyAppName}
; Güncellemede çalışan uygulama kapatılır (dosya kilidi engeli olmasın)
CloseApplications=yes
RestartApplications=no
OutputDir=..\dist\installer
OutputBaseFilename=KaynakYonetimPlatformu-Setup-{#AppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\icon.ico

[Files]
Source: "..\dist\KaynakYonetimPlatformu\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; GroupDescription: "Ek kısayollar:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} uygulamasını başlat"; Flags: nowait postinstall skipifsilent
; Sessiz güncelleme sonrası otomatik yeniden başlatma (/VERYSILENT denemesinde açmaz)
Filename: "{app}\{#MyAppExeName}"; Flags: nowait; Check: RelaunchAfterUpdate

[Code]
function HasParam(const Name: String): Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount do
  begin
    if CompareText(ParamStr(I), Name) = 0 then
    begin
      Result := True;
      Exit;
    end;
  end;
end;

function RelaunchAfterUpdate: Boolean;
begin
  Result := WizardSilent and not HasParam('/VERYSILENT');
end;
