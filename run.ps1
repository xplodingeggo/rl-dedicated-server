# Launch the headless server from the copy built by setup.ps1.   .\run.ps1 [-Dir .\game] [-Map Stadium_P] [-Extra '...']
# -Map must match the one given to setup.ps1: the server boots on it, then travels to the URL baked into ProjectX.upk.
param([string]$Dir = "$PSScriptRoot\game", [string]$Map = 'Stadium_P', [string]$Extra = '')
$g = "$Dir\Binaries\Win64"
if (-not (Test-Path "$g\RocketLeague_Server.exe")) { throw "No server build in $Dir - run setup.ps1 first" }
Start-Process "$g\RocketLeague_Server.exe" -WorkingDirectory $g -PassThru -ArgumentList "server $Map`?game=TAGame.GameInfo_Soccar_TA`?Private`?playtest`?listen -FakeServer -noeac -nullrhi -nosound -unattended -log -nostartupmovies $Extra"
