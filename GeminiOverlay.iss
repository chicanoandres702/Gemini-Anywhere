; GeminiOverlay.iss
; Inno Setup script for Gemini Everywhere (Auto-Py-to-Exe version)
; IMPORTANT: This version uses an ABSOLUTE PATH and is NOT for general distribution.

[Setup]
AppName=Gemini Everywhere
AppVersion=1.0
DefaultDirName={pf}\Gemini Everywhere
DisableDirPage=no
OutputDir=.\output
OutputBaseFilename=GeminiEverywhere-Installer
Compression=lzma
SolidCompression=yes
UninstallDisplayIcon={app}\GeminiEverywhere.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "C:\Users\Andrew\PycharmProjects\GeminiAnywhere\output\Gemini Everywhere.exe"; DestDir: "{app}"; DestName: "GeminiEverywhere.exe"
Source: "C:\Users\Andrew\PycharmProjects\GeminiAnywhere\output\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs; Excludes: "Gemini Everywhere.exe";

; Add any other necessary files from your build directory here

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "GeminiEverywhere"; ValueData: """{app}\GeminiEverywhere.exe"""; Flags: uninsdeletevalue

[Icons]
Name: "{userprograms}\Gemini Everywhere"; Filename: "{app}\GeminiEverywhere.exe"; IconFilename: "{app}\GeminiEverywhere.exe"
Name: "{commondesktop}\Gemini Everywhere"; Filename: "{app}\GeminiEverywhere.exe"; Tasks: desktopicon; IconFilename: "{app}\GeminiEverywhere.exe"

[UninstallDelete]
; Comment this out as deltree handles it
; Type: files; Name: "{app}\*"
; Type: dirifempty; Name: "{app}"

[Run]
Filename: "{app}\GeminiEverywhere.exe"; Description: "Launch Gemini Everywhere"; Flags: postinstall nowait skipifdoesntexist

[Code]
function DelTree(DirName: String): Boolean;
begin
    begin
      if not RemoveDir(DirName) then
        begin
         Log('DelTree failed: ' + DirName);
         Result := False;
        end
        else
           Result := True;
    end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
    if CurUninstallStep = usUninstall then
    begin
      // Delete the specific value of your application
      RegDeleteValue(HKEY_CURRENT_USER, 'Software\Microsoft\Windows\CurrentVersion\Run', 'GeminiEverywhere');

      // Delete all files and directories in application directory
      if not DelTree(ExpandConstant('{app}')) then
        MsgBox('Error removing folder at ' + ExpandConstant('{app}'), mbError, MB_OK);
    end;
end;