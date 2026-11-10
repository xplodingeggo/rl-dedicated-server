#!/usr/bin/env bash
# Build a private server copy of the game. Your real install is only read, never modified.
#   ./setup.sh <game dir> [out dir, default ./game] [map, default MAP from server.conf or Stadium_P]
#   (no arguments: GAME_DIR and OUT_DIR from server.conf, written by install.sh)
# e.g. ./setup.sh ~/.local/share/Steam/steamapps/common/rocketleague
# PYTHON=/path/to/python picks the interpreter for the patchers (install.sh sets it to the repo's venv).
# Textures (.tfc) and audio streams (.wem/.ewem) are skipped: the server runs with -nullrhi -nosound (~11 GB instead of ~30).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
py="${PYTHON:-python3}"
# conf_get KEY: value of KEY=... in server.conf (empty when missing). Read as text, never sourced.
conf_get() { [ -f "$here/server.conf" ] && grep -m1 "^$1=" "$here/server.conf" | cut -d= -f2- || true; }
game="${1:-$(conf_get GAME_DIR)}"
[ -n "$game" ] || { echo "usage: ./setup.sh <game dir> [out dir] [map]  (or run install.sh first)" >&2; exit 1; }
out="${2:-$(conf_get OUT_DIR)}"
out="${out:-$here/game}"
map="${3:-$(conf_get MAP)}"; map="${map:-Stadium_P}"

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

# Guard: setup removes $out first. Refuse anything that is not clearly our own copy.
out_abs="$(realpath -m "$out")"; game_abs="$(realpath -m "$game")"
[ "$out_abs" != / ] && [ "$out_abs" != "$HOME" ] || { echo "refusing to use $out_abs as the server folder" >&2; exit 1; }
case "$game_abs/" in "$out_abs/"*) echo "server folder $out_abs contains the game folder; refusing" >&2; exit 1 ;; esac
case "$here/" in "$out_abs/"*) echo "server folder $out_abs contains this repo; refusing" >&2; exit 1 ;; esac
case "$out_abs/" in "$game_abs/"*) echo "server folder $out_abs is inside the game folder; refusing" >&2; exit 1 ;; esac
if [ -d "$out" ] && [ -n "$(ls -A "$out")" ] && [ ! -f "$out/.rl-server-copy" ] && [ ! -f "$out/Binaries/Win64/RocketLeague_Server.exe" ]; then
    echo "$out is not empty and is not a server copy; refusing to delete it. Pick an empty folder." >&2; exit 1
fi

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
"$py" -X utf8 -I "$here/patch_upk.py" "$cooked" "$out/TAGame/CookedPCConsole" "$map"
"$py" -X utf8 -I "$here/patch_exe.py" "$exe" "$out/Binaries/Win64/RocketLeague_Server.exe"
echo "$map" > "$out/.rl-server-copy"   # the map baked into this copy; run.sh warns when asked for another
echo "Server copy ready: $out   start it with ./run.sh --dir '$out' --map $map"
