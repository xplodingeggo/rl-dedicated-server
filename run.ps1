# Launch the headless server from the copy built by setup.ps1.   .\run.ps1 [-Dir .\game] [-Map Stadium_P] [-Name 'My server'] [-Extra '...']
# -Map must match the one given to setup.ps1: the server boots on it, then travels to the URL baked into ProjectX.upk.
# Also starts lan_responder.py, which makes the server show up in the game's LAN match browser.
# -Logs opens a window that follows the server's log file; selecting text there only pauses that window, not the server.
param([string]$Dir = "$PSScriptRoot\game", [string]$Map = 'Stadium_P', [string]$Name = 'Dedicated server', [string]$Extra = '', [switch]$Logs)
$g = "$Dir\Binaries\Win64"
if (-not (Test-Path "$g\RocketLeague_Server.exe")) { throw "No server build in $Dir - run setup.ps1 first" }
# Hidden: clicking into the -log console window starts a text selection, which pauses console writes and freezes the server.
Start-Process "$g\RocketLeague_Server.exe" -WorkingDirectory $g -WindowStyle Hidden -PassThru -ArgumentList "server $Map`?game=TAGame.GameInfo_Soccar_TA`?Lan`?listen -FakeServer -noeac -nullrhi -nosound -unattended -log -nostartupmovies $Extra"
Start-Process python -WindowStyle Hidden -PassThru -ArgumentList '-X', 'utf8', '-I', "`"$PSScriptRoot\lan_responder.py`"", $Map, "`"$Name`""
if ($Logs) {
    # Launch.log, or Launch_2.log when a game client already holds Launch.log: the server's is the one naming -FakeServer
    $tail = {
        $d = [Environment]::GetFolderPath('MyDocuments') + '\My Games\Rocket League\TAGame\Logs'
        Start-Sleep 5
        $f = Get-ChildItem "$d\Launch.log", "$d\Launch_2.log" -ErrorAction SilentlyContinue |
            Where-Object { Select-String $_.FullName -Pattern 'FakeServer' -Quiet } | Sort-Object LastWriteTime | Select-Object -Last 1
        $Host.UI.RawUI.WindowTitle = "RL server log: $($f.Name)"
        Get-Content $f.FullName -Wait -Tail 100
    }
    Start-Process powershell -ArgumentList '-NoExit', '-NoProfile', '-Command', "& {$tail}"
}
