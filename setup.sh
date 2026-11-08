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

# ci <dir> <name>...: the path dir/name/... with every part matched ignoring case (the game's files are named for
# Windows; this file system may be case sensitive). Fails when a part is missing.
ci() {
    local p="$1" hit; shift
    for n in "$@"; do
        hit="$(find "$p" -maxdepth 1 -iname "$n" -print -quit 2>/dev/null)"
        [ -n "$hit" ] || return 1
        p="$hit"
    done
    echo "$p"
}

exe="$(ci "$game" Binaries Win64 RocketLeague.exe)" || { echo "RocketLeague.exe not found under $game/Binaries/Win64" >&2; exit 1; }
win64="$(dirname "$exe")"
engine="$(ci "$game" Engine)" || { echo "Engine folder not found under $game" >&2; exit 1; }
tagame="$(ci "$game" TAGame)" || { echo "TAGame folder not found under $game" >&2; exit 1; }
upk="$(ci "$game" TAGame.upk)" || { echo "TAGame.upk not found under $game" >&2; exit 1; }
cooked="$(ci "$tagame" CookedPCConsole)" || { echo "CookedPCConsole not found under $tagame" >&2; exit 1; }

rm -rf "$out"
mkdir -p "$out/Binaries" "$out/TAGame/CookedPCConsole"
cp -r "$engine" "$out/Engine"
cp -r "$win64" "$out/Binaries/Win64"
rm "$out/Binaries/Win64/$(basename "$exe")"
cp "$upk" "$out/"
for f in "$tagame"/* "$tagame"/.[!.]*; do
    [ -e "$f" ] || continue
    [ "$(basename "$f" | tr '[:upper:]' '[:lower:]')" = cookedpcconsole ] || cp -r "$f" "$out/TAGame/"
done
# The game scans CookedPCConsole recursively, so mod-manager folders are left out to avoid duplicate packages.
(cd "$cooked" && find . -type f \( -iname '*.upk' -o -iname '*.bin' -o -iname '*.udk' -o -iname '*.bnk' -o -iname '*.ebnk' -o -iname '*.py' \) \
    -not -ipath './mods/*' -not -ipath './Backups/*' -not -ipath './.hebnix-menu-map/*' -print0 \
    | xargs -0 cp --parents -t "$out/TAGame/CookedPCConsole")
python3 -X utf8 -I "$here/patch_upk.py" "$cooked" "$out/TAGame/CookedPCConsole" "$map"
python3 -X utf8 -I "$here/patch_exe.py" "$exe" "$out/Binaries/Win64/RocketLeague_Server.exe"
echo "Server copy ready: $out   start it with ./run.sh --dir '$out' --map $map"
