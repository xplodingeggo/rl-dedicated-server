#!/usr/bin/env bash
# Build a private server copy of the game. Your real install is only read, never modified.
#   ./setup.sh <game dir> [out dir, default ./game] [map, default Stadium_P]
# e.g. ./setup.sh ~/.local/share/Steam/steamapps/common/rocketleague
# Textures (.tfc) and audio streams (.wem/.ewem) are skipped: the server runs with -nullrhi -nosound (~11 GB instead of ~30).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
game="${1:?usage: ./setup.sh <game dir> [out dir] [map]}"
out="${2:-$here/game}"
map="${3:-Stadium_P}"
[ -f "$game/Binaries/Win64/RocketLeague.exe" ] || { echo "RocketLeague.exe not found under $game/Binaries/Win64" >&2; exit 1; }
rm -rf "$out"
mkdir -p "$out/Binaries" "$out/TAGame/CookedPCConsole"
cp -r "$game/Engine" "$out/Engine"
cp -r "$game/Binaries/Win64" "$out/Binaries/Win64"
rm "$out/Binaries/Win64/RocketLeague.exe"
cp "$game/TAGame.upk" "$out/"
for f in "$game"/TAGame/* "$game"/TAGame/.[!.]*; do
    [ -e "$f" ] && [ "$(basename "$f")" != CookedPCConsole ] && cp -r "$f" "$out/TAGame/"
done
# The game scans CookedPCConsole recursively, so mod-manager folders are left out to avoid duplicate packages.
(cd "$game/TAGame/CookedPCConsole" && find . -type f \( -iname '*.upk' -o -iname '*.bin' -o -iname '*.udk' -o -iname '*.bnk' -o -iname '*.ebnk' -o -iname '*.py' \) \
    -not -path './mods/*' -not -path './Backups/*' -not -path './.hebnix-menu-map/*' -print0 \
    | xargs -0 cp --parents -t "$out/TAGame/CookedPCConsole")
python3 -X utf8 -I "$here/patch_upk.py" "$game/TAGame/CookedPCConsole" "$out/TAGame/CookedPCConsole" "$map"
python3 -X utf8 -I "$here/patch_exe.py" "$game/Binaries/Win64/RocketLeague.exe" "$out/Binaries/Win64/RocketLeague_Server.exe"
echo "Server copy ready: $out   start it with ./run.sh --dir '$out' --map $map"
