# Launch the headless server from the copy built by setup.ps1.   .\run.ps1 [-Dir .\game] [-Map Stadium_P] [-Name 'My server'] [-Extra '...']
# -Map must match the one given to setup.ps1: the server boots on it, then travels to the URL baked into ProjectX.upk.
# Also starts lan_responder.py, which makes the server show up in the game's LAN match browser.
param([string]$Dir = "$PSScriptRoot\game", [string]$Map = 'Stadium_P', [string]$Name = 'Dedicated server', [string]$Extra = '')
$g = "$Dir\Binaries\Win64"
if (-not (Test-Path "$g\RocketLeague_Server.exe")) { throw "No server build in $Dir - run setup.ps1 first" }
Start-Process "$g\RocketLeague_Server.exe" -WorkingDirectory $g -PassThru -ArgumentList "server $Map`?game=TAGame.GameInfo_Soccar_TA`?Lan`?listen -FakeServer -noeac -nullrhi -nosound -unattended -log -nostartupmovies $Extra"
Start-Process python -WindowStyle Hidden -PassThru -ArgumentList '-X', 'utf8', '-I', "`"$PSScriptRoot\lan_responder.py`"", $Map, "`"$Name`""
