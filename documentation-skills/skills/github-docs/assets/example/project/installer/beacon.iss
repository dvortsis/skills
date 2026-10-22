; Synthetic Inno Setup script for the github-docs example project.
[Setup]
AppName=Beacon
AppVersion=2.4.0
AppPublisher=Example Beacon Contributors
DefaultDirName={autopf}\Beacon
PrivilegesRequired=admin

[Dirs]
Name: "{commonappdata}\Beacon"

[Run]
Filename: "{sys}\sc.exe"; Parameters: "create Beacon binPath= ""{app}\beacon.exe --service"" start= auto"; Flags: runhidden
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=Beacon dir=in action=allow protocol=TCP localport=8484 profile=private"; Flags: runhidden
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=BeaconPeers dir=in action=allow protocol=UDP localport=6990 profile=private"; Flags: runhidden
