# Paste-a-link installer for Windows. It asks a few questions, then builds the server copy.
#   irm https://raw.githubusercontent.com/xplodingeggo/rl-dedicated-server/main/install.ps1 | iex
# Skip the questions with parameters: -Repo, -Game, -Out, -Yes. Your real game install is only read.
# Not yet tested on Windows: the Linux installer (install.sh) is the one that has been run end to end.
param([string]$Repo, [string]$Game, [string]$Out, [string]$Map, [switch]$Yes)
$ErrorActionPreference = 'Stop'
$RepoUrl = 'https://github.com/xplodingeggo/rl-dedicated-server'

function Ask($question, $default) {
    if ($Yes) { return $default }
    $answer = Read-Host "$question [$default]"
    if ([string]::IsNullOrWhiteSpace($answer)) { return $default }
    return $answer
}
function Choose($title, $labels, $values) {
    if ($Yes -or $labels.Count -eq 0) { return $values[0] }
    Write-Host ""; Write-Host $title
    for ($i = 0; $i -lt $labels.Count; $i++) { Write-Host "  $($i + 1)) $($labels[$i])" }
    while ($true) {
        $pick = Read-Host "choose 1-$($labels.Count) [1]"
        if ([string]::IsNullOrWhiteSpace($pick)) { $pick = '1' }
        if ($pick -match '^\d+$' -and [int]$pick -ge 1 -and [int]$pick -le $labels.Count) { return $values[[int]$pick - 1] }
    }
}
function Is-Game($dir) { $dir -and (Test-Path "$dir\Binaries\Win64\RocketLeague.exe") }

# ---- 0. python -----------------------------------------------------------------
$pyExe = $null; $pyPre = @()
foreach ($cand in @(@('py', @('-3')), @('python', @()))) {
    if (-not (Get-Command $cand[0] -ErrorAction SilentlyContinue)) { continue }
    $ok = & $cand[0] @($cand[1]) -c 'import sys; print(sys.version_info >= (3, 10))' 2>$null
    if ($ok -eq 'True') { $pyExe = $cand[0]; $pyPre = $cand[1]; break }
}
if (-not $pyExe) { throw 'Python 3.10 or newer not found. Install it from python.org (tick "Add to PATH").' }

# ---- 1. repo -------------------------------------------------------------------
$Repo = if ($Repo) { $Repo } else { Ask 'where to keep the repo' "$HOME\rl-dedicated-server" }
if (Test-Path "$Repo\.git") {
    git -C $Repo pull --ff-only --quiet
} elseif (Test-Path $Repo) {
    throw "$Repo exists but is not a clone of the repo"
} elseif (Get-Command git -ErrorAction SilentlyContinue) {
    git clone --quiet $RepoUrl $Repo
} else {
    $zip = "$env:TEMP\rl-dedicated-server.zip"
    Invoke-WebRequest "$RepoUrl/archive/refs/heads/main.zip" -OutFile $zip
    Expand-Archive $zip -DestinationPath "$env:TEMP\rl-dedicated-zip" -Force
    Move-Item "$env:TEMP\rl-dedicated-zip\rl-dedicated-server-main" $Repo
}

# ---- 2. python packages in a venv ----------------------------------------------
if (-not (Test-Path "$Repo\.venv\Scripts\python.exe")) { & $pyExe @pyPre -m venv "$Repo\.venv" }
& "$Repo\.venv\Scripts\python.exe" -m pip install -q -r "$Repo\requirements.txt"
$env:PYTHON = "$Repo\.venv\Scripts\python.exe"

# ---- 3. game folder --------------------------------------------------------------
if (-not $Game) {
    $labels = @(); $values = @()
    $steam = (Get-ItemProperty 'HKCU:\Software\Valve\Steam' -ErrorAction SilentlyContinue).SteamPath
    if ($steam) {
        $steam = $steam -replace '/', '\'
        $libs = @($steam)
        $vdf = "$steam\steamapps\libraryfolders.vdf"
        if (Test-Path $vdf) {
            $libs += Select-String $vdf -Pattern '"path"\s+"(.+?)"' | ForEach-Object { $_.Matches[0].Groups[1].Value -replace '\\\\', '\' }
        }
        foreach ($lib in $libs | Select-Object -Unique) {
            $d = "$lib\steamapps\common\rocketleague"
            if (Is-Game $d) { $labels += "Steam: $d"; $values += $d }
        }
    }
    $epicFile = 'C:\ProgramData\Epic\UnrealEngineLauncher\LauncherInstalled.dat'
    if (Test-Path $epicFile) {
        $sugar = (Get-Content $epicFile -Raw | ConvertFrom-Json).InstallationList | Where-Object { $_.AppName -eq 'Sugar' }
        if ($sugar -and (Is-Game $sugar.InstallLocation)) { $labels += "Epic: $($sugar.InstallLocation)"; $values += $sugar.InstallLocation }
    }
    $labels += 'other: type a path'; $values += ''
    $Game = Choose 'Rocket League install (read only, never changed):' $labels $values
    if (-not $Game) { $Game = Ask 'path to the Rocket League folder (the one with Binaries\Win64)' '' }
}
if (-not (Is-Game $Game)) { throw "RocketLeague.exe not found under $Game\Binaries\Win64" }

# ---- 4. server copy folder --------------------------------------------------------
if (-not $Out) { $Out = Ask 'where to put the server copy (about 11 GB)' "$Repo\game" }
$existing = [IO.Path]::GetFullPath($Out)
while (-not (Test-Path $existing)) { $existing = Split-Path $existing -Parent }
$freeGb = [math]::Floor((Get-Item $existing).PSDrive.Free / 1GB)
if ($freeGb -lt 12) { Write-Warning "only $freeGb GB free under $existing; the copy needs about 11 GB" }

# ---- 4b. starting map (baked into the copy; see README, Choosing the map) -----
if (-not $Map) { $Map = Ask 'map the server starts on' 'Stadium_P' }

# ---- 5. remember and build -----------------------------------------------------------
@("GAME_DIR=$Game", "OUT_DIR=$Out", "MAP=$Map", "PYTHON=$env:PYTHON") | Set-Content "$Repo\server.conf"
Write-Host "saved choices to $Repo\server.conf"
Push-Location $Repo
try { & .\setup.ps1 -Game $Game -Out $Out -Map $Map } finally { Pop-Location }

# ---- 6. start ----------------------------------------------------------------------------
if ((Ask 'start the server now? (y/n)' 'n') -match '^[yY]') {
    $name = Ask 'server name shown in the LAN browser' 'Dedicated server'
    $join = Ask 'join password (blank for none)' ''
    $admin = Ask 'admin password (blank for none)' ''
    $runArgs = @{ Dir = $Out; Map = $Map; Name = $name; NoLog = $true }
    if ($join) { $runArgs.JoinPassword = $join }
    if ($admin) { $runArgs.AdminPassword = $admin }
    & "$Repo\run.ps1" @runArgs
}
Write-Host ""
Write-Host "done. Server copy: $Out"
Write-Host "start: cd $Repo; .\run.ps1 -Name 'My server'"
Write-Host "stop:  cd $Repo; .\stop.ps1"
