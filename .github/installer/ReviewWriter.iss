#ifndef APP_VERSION
  #define APP_VERSION "0.0.0"
#endif

#define MyAppName "Review Writer"
#define MyAppPublisher "SSMakers"
#define MyAppExeName "Review_Program.exe"

[Setup]
AppId={{4A3D6F6E-9D8A-4E9D-83A2-2E3B6F8C1A77}
AppName={#MyAppName}
AppVersion={#APP_VERSION}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Review Writer
DefaultGroupName=Review Writer
DisableDirPage=yes
OutputDir=dist
OutputBaseFilename=ReviewWriterSetup_{#APP_VERSION}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=yes

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Files]
Source: "dist\Review_Program\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Review Writer"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Review Writer"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Flags: nowait skipifnotsilent
Filename: "{app}\{#MyAppExeName}"; Description: "Review Writer 실행"; Flags: nowait postinstall skipifsilent
