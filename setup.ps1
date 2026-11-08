# Build a private server copy of the game. Your real install is only read, never modified.
#   .\setup.ps1 -Game 'C:\Program Files (x86)\Steam\steamapps\common\rocketleague' [-Out .\game] [-Map Stadium_P]
# Textures (.tfc) and audio streams (.wem/.ewem) are skipped: the server runs with -nullrhi -nosound (~11 GB instead of ~30).
param(
    [Parameter(Mandatory)][string]$Game,
    [string]$Out = "$PSScriptRoot\game",
    [string]$Map = 'Stadium_P'
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path "$Game\Binaries\Win64\RocketLeague.exe")) { throw "RocketLeague.exe not found under $Game\Binaries\Win64" }
if (Test-Path $Out) { cmd /c rmdir /s /q $Out }
New-Item -ItemType Directory -Force "$Out\Binaries", "$Out\TAGame\CookedPCConsole" | Out-Null
Copy-Item "$Game\Engine" "$Out\Engine" -Recurse
Copy-Item "$Game\Binaries\Win64" "$Out\Binaries\Win64" -Recurse
Remove-Item "$Out\Binaries\Win64\RocketLeague.exe"
Copy-Item "$Game\TAGame.upk" $Out
Get-ChildItem "$Game\TAGame" -Force | ? { $_.Name -ne 'CookedPCConsole' } | % { Copy-Item $_.FullName "$Out\TAGame\$($_.Name)" -Recurse }
# The game scans CookedPCConsole recursively, so mod-manager folders are left out to avoid duplicate packages.
robocopy "$Game\TAGame\CookedPCConsole" "$Out\TAGame\CookedPCConsole" *.upk *.bin *.udk *.bnk *.ebnk *.py /XD mods Backups .hebnix-menu-map /NFL /NDL /NJH /NP /MT:16 | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed ($LASTEXITCODE)" }
python -X utf8 -I "$PSScriptRoot\patch_upk.py" "$Game\TAGame\CookedPCConsole" "$Out\TAGame\CookedPCConsole" $Map
if ($LASTEXITCODE) { throw 'package patch failed' }
python -X utf8 -I "$PSScriptRoot\patch_exe.py" "$Game\Binaries\Win64\RocketLeague.exe" "$Out\Binaries\Win64\RocketLeague_Server.exe"
if ($LASTEXITCODE) { throw 'exe patch failed' }
"Server copy ready: $Out   start it with .\run.ps1 -Dir '$Out' -Map $Map"
