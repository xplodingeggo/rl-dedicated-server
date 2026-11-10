# Build a private server copy of the game. Your real install is only read, never modified.
#   .\setup.ps1 -Game 'C:\Program Files (x86)\Steam\steamapps\common\rocketleague' [-Out .\game] [-Map Stadium_P]
# Textures (.tfc) and audio streams (.wem/.ewem) are skipped: the server runs with -nullrhi -nosound (~11 GB instead of ~30).
param(
    [Parameter(Mandatory)][string]$Game,
    [string]$Out = "$PSScriptRoot\game",
    [string]$Map = 'Stadium_P'
)
$ErrorActionPreference = 'Stop'
$py = if ($env:PYTHON) { $env:PYTHON } else { 'python' }   # install.ps1 sets this to the repo's venv
if (-not (Test-Path "$Game\Binaries\Win64\RocketLeague.exe")) { throw "RocketLeague.exe not found under $Game\Binaries\Win64" }
# Guard: the next line deletes $Out. Refuse anything that is not clearly our own copy.
$outFull = [IO.Path]::GetFullPath($Out).TrimEnd('\')
$gameFull = [IO.Path]::GetFullPath($Game).TrimEnd('\')
if ($outFull -eq [IO.Path]::GetPathRoot($outFull).TrimEnd('\') -or $outFull -ieq [Environment]::GetFolderPath('UserProfile') -or $outFull -ieq $PSScriptRoot) { throw "refusing to use $outFull as the server folder" }
if ($gameFull.StartsWith("$outFull\", [StringComparison]::OrdinalIgnoreCase) -or $outFull.StartsWith("$gameFull\", [StringComparison]::OrdinalIgnoreCase)) { throw "server folder $outFull overlaps the game folder; refusing" }
if ($PSScriptRoot.StartsWith("$outFull\", [StringComparison]::OrdinalIgnoreCase)) { throw "server folder $outFull contains this repo; refusing" }
if ((Test-Path $Out) -and (Get-ChildItem $Out -Force | Select-Object -First 1) -and -not (Test-Path "$Out\.rl-server-copy") -and -not (Test-Path "$Out\Binaries\Win64\RocketLeague_Server.exe")) { throw "$Out is not empty and is not a server copy; refusing to delete it" }
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
$py -X utf8 -I "$PSScriptRoot\patch_upk.py" "$Game\TAGame\CookedPCConsole" "$Out\TAGame\CookedPCConsole" $Map
if ($LASTEXITCODE) { throw 'package patch failed' }
$py -X utf8 -I "$PSScriptRoot\patch_exe.py" "$Game\Binaries\Win64\RocketLeague.exe" "$Out\Binaries\Win64\RocketLeague_Server.exe"
if ($LASTEXITCODE) { throw 'exe patch failed' }
Set-Content "$Out\.rl-server-copy" $Map   # the map baked into this copy
"Server copy ready: $Out   start it with .\run.ps1 -Dir '$Out' -Map $Map"
