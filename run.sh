#!/usr/bin/env bash
# Launch the headless server (under Wine) from the copy built by setup.sh, plus lan_responder.py for the LAN browser.
#   ./run.sh [--dir ./game] [--map Stadium_P] [--name 'My server'] [--extra '...'] [--join-password pw] [--admin-password pw] [--logs]
# Same options as run.ps1. Set WINEPREFIX to use a prefix other than ~/.wine, e.g. Steam's Proton one:
#   WINEPREFIX=~/.local/share/Steam/steamapps/compatdata/252950/pfx ./run.sh
# Stop it with ./run.sh --stop
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dir="$here/game"; map=Stadium_P; name='Dedicated server'; extra=''; join=''; admin=''; logs=0
while [ $# -gt 0 ]; do
    case "$1" in
        --dir) dir="$2"; shift 2 ;;
        --map) map="$2"; shift 2 ;;
        --name) name="$2"; shift 2 ;;
        --extra) extra="$2"; shift 2 ;;
        --join-password) join="$2"; shift 2 ;;
        --admin-password) admin="$2"; shift 2 ;;
        --logs) logs=1; shift ;;
        --stop) pkill -f RocketLeague_Server.exe || true; pkill -f lan_responder.py || true; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 1 ;;
    esac
done
for p in "$join" "$admin"; do
    case "$p" in *[[:space:]\"]*) echo 'Passwords cannot contain spaces or quotes' >&2; exit 1 ;; esac
done
[ -n "$join" ] && extra="$extra -JoinPassword=$join"
[ -n "$admin" ] && extra="$extra -AdminPassword=$admin"
g="$dir/Binaries/Win64"
[ -f "$g/RocketLeague_Server.exe" ] || { echo "No server build in $dir - run setup.sh first" >&2; exit 1; }
command -v wine >/dev/null || { echo 'wine not found: install Wine (or set WINE=/path/to/wine)' >&2; exit 1; }
cd "$g"
# $extra is split on purpose: it holds several command line options
# shellcheck disable=SC2086
nohup "${WINE:-wine}" RocketLeague_Server.exe "server $map?game=TAGame.GameInfo_Soccar_TA?Lan?listen" \
    -FakeServer -noeac -nullrhi -nosound -unattended -log -nostartupmovies -forcelogflush $extra >/dev/null 2>&1 &
resp=(-X utf8 -I "$here/lan_responder.py" "$map" "$name")
[ -n "$join" ] && resp+=(-p)   # only tells the LAN browser the server has a password; the server checks it
nohup python3 "${resp[@]}" >/dev/null 2>&1 &
echo "started: server (wine) and lan_responder"
if [ "$logs" = 1 ]; then
    prefix="${WINEPREFIX:-$HOME/.wine}"
    sleep 5
    # Launch.log, or Launch_2.log when a game client already holds Launch.log: the server's is the one naming -FakeServer
    f="$(grep -l FakeServer "$prefix"/drive_c/users/*/Documents/My\ Games/Rocket\ League/TAGame/Logs/Launch*.log 2>/dev/null | xargs -r ls -t | head -1)"
    [ -n "$f" ] || { echo "server log not found under $prefix" >&2; exit 1; }
    exec tail -n 100 -F "$f"
fi
