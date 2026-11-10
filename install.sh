#!/usr/bin/env bash
# Paste-a-link installer for the Linux (Wine) setup. It asks a few questions, then builds the server copy.
#   curl -fsSL https://raw.githubusercontent.com/xplodingeggo/rl-dedicated-server/main/install.sh | bash
# Skip questions with flags (add --yes to take the first choice for anything not given):
#   --repo DIR  --game DIR  --out DIR  --map NAME  --wine PATH  --prefix DIR  --yes
# Your real game install is only read. The server copy and the Wine prefix are the only things written.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/xplodingeggo/rl-dedicated-server}"
MIN_FREE_GB=12

die() { echo "error: $*" >&2; exit 1; }
say() { printf '%s\n' "$*" >&2; }

REPO=""; GAME=""; OUT=""; MAP=""; WINE=""; PREFIX=""; ASSUME_YES=""
while [ $# -gt 0 ]; do
    case "$1" in
        --repo) REPO="$2"; shift 2 ;;
        --game) GAME="$2"; shift 2 ;;
        --out) OUT="$2"; shift 2 ;;
        --map) MAP="$2"; shift 2 ;;
        --wine) WINE="$2"; shift 2 ;;
        --prefix) PREFIX="$2"; shift 2 ;;
        --yes) ASSUME_YES=1; shift ;;
        *) die "unknown option: $1" ;;
    esac
done

# ask "question" default -> answer on stdout
ask() {
    local ans
    if [ -n "$ASSUME_YES" ]; then printf '%s\n' "$2"; return; fi
    [ -r /dev/tty ] || die "no terminal to ask on; pass the answers as flags (see the top of this file)"
    read -r -p "$1 [$2]: " ans </dev/tty || die "no answer"
    printf '%s\n' "${ans:-$2}"
}

# menu "title": choices come from the LBL and VAL arrays (set by add). Chosen value on stdout.
LBL=(); VAL=()
add() { LBL+=("$1"); VAL+=("$2"); }
menu() {
    local pick i
    if [ -n "$ASSUME_YES" ]; then printf '%s\n' "${VAL[0]}"; LBL=(); VAL=(); return; fi
    say ""; say "$1"
    for i in "${!LBL[@]}"; do say "  $((i + 1))) ${LBL[$i]}"; done
    [ -r /dev/tty ] || die "no terminal to ask on; pass the answers as flags (see the top of this file)"
    while :; do
        read -r -p "choose 1-${#LBL[@]} [1]: " pick </dev/tty || die "no answer"
        pick="${pick:-1}"
        if [[ "$pick" =~ ^[0-9]+$ ]] && [ "$pick" -ge 1 ] && [ "$pick" -le "${#LBL[@]}" ]; then
            printf '%s\n' "${VAL[$((pick - 1))]}"; LBL=(); VAL=(); return
        fi
    done
}

shopt -s nullglob
steam_roots() {
    local r
    for r in "$HOME/.local/share/Steam" "$HOME/.steam/root" "$HOME/.steam/steam"; do
        [ -d "$r/steamapps" ] && realpath "$r"
    done | sort -u
}
is_game() { [ -n "$(find "$1" -maxdepth 3 -ipath '*/binaries/win64/rocketleague.exe' -print -quit 2>/dev/null)" ]; }
json_get() {  # json_get FILE 'python expression on d' -> value or empty
    python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print($2 or '')" "$1" 2>/dev/null || true
}

# ---- 0. tools -----------------------------------------------------------------
command -v git >/dev/null || die "git not found: install it (e.g. sudo pacman -S git / sudo apt install git)"
command -v python3 >/dev/null || die "python3 not found: install Python 3.10 or newer"
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || die "Python 3.10 or newer needed"

# ---- 1. repository ------------------------------------------------------------
here=""
src="${BASH_SOURCE[0]:-}"
if [ -n "$src" ] && [ -f "$src" ] && [ -f "$(dirname "$src")/setup.sh" ]; then here="$(cd "$(dirname "$src")" && pwd)"; fi
REPO="${REPO:-}"
[ -n "$REPO" ] || REPO="$(ask "where to keep the repo" "${here:-$HOME/rl-dedicated-server}")"
REPO="$(realpath -m "$REPO")"
if [ -d "$REPO/.git" ]; then
    git -C "$REPO" pull --ff-only -q || say "warning: could not update $REPO, using what is there"
elif [ -e "$REPO" ]; then
    die "$REPO exists but is not a git clone of the repo"
else
    git clone -q "$REPO_URL" "$REPO"
fi

# ---- 2. python packages (own venv: avoids the "externally managed" error on Arch and Debian) ----
if [ ! -x "$REPO/.venv/bin/python" ]; then
    python3 -m venv "$REPO/.venv" || die "could not create a venv (on Debian/Ubuntu: sudo apt install python3-venv)"
fi
"$REPO/.venv/bin/pip" install -q -r "$REPO/requirements.txt"
PY="$REPO/.venv/bin/python"

# ---- 3. game folder -----------------------------------------------------------
if [ -z "$GAME" ]; then
    LBL=(); VAL=()
    for root in $(steam_roots); do
        libs="$(grep -o '"path"[[:space:]]*"[^"]*"' "$root/steamapps/libraryfolders.vdf" 2>/dev/null | sed 's/.*"\([^"]*\)"$/\1/' || true)"
        for lib in $root $libs; do
            d="$lib/steamapps/common/rocketleague"
            is_game "$d" && add "Steam: $d" "$d"
        done
    done
    epic="$(json_get "$HOME/.config/heroic/legendaryConfig/legendary/installed.json" "d.get('Sugar',{}).get('install_path')")"
    [ -n "$epic" ] && is_game "$epic" && add "Epic via Heroic: $epic" "$epic"
    add "other: type a path" ""
    GAME="$(menu "Rocket League install (read only, never changed):")"
    [ -n "$GAME" ] || GAME="$(ask "path to the Rocket League folder (the one with Binaries/Win64)" "")"
fi
GAME="$(realpath -m "$GAME")"
is_game "$GAME" || die "RocketLeague.exe not found under $GAME/Binaries/Win64"

# ---- 4. server copy folder ----------------------------------------------------
[ -n "$OUT" ] || OUT="$(ask "where to put the server copy (about 11 GB)" "$REPO/game")"
OUT="$(realpath -m "$OUT")"
p="$OUT"; while [ ! -d "$p" ]; do p="$(dirname "$p")"; done
free="$(df -BG --output=avail "$p" | tail -1 | tr -dc '0-9')"
[ "${free:-0}" -ge "$MIN_FREE_GB" ] || say "warning: only ${free} GB free under $p; the copy needs about 11 GB"

# ---- 4b. starting map (baked into the copy; see README, Choosing the map) -----
[ -n "$MAP" ] || MAP="$(ask "map the server starts on" "Stadium_P")"

# ---- 5. Wine -------------------------------------------------------------------
if [ -z "$WINE" ]; then
    LBL=(); VAL=()
    command -v wine >/dev/null && add "system wine $(wine --version 2>/dev/null): $(command -v wine)" "$(command -v wine)"
    for root in $(steam_roots) /usr/share/steam; do
        for d in "$root"/compatibilitytools.d/*/; do
            [ -x "$d/files/bin/wine64" ] && add "Proton/GE-Proton: $(basename "$d") (Steam)" "$d/files/bin/wine64"
        done
    done
    for d in "$HOME"/.config/heroic/tools/wine/*/ "$HOME"/.config/heroic/tools/proton/*/; do
        [ -x "$d/bin/wine" ] && add "Heroic wine: $(basename "$d")" "$d/bin/wine"
        [ -x "$d/files/bin/wine64" ] && add "Heroic Proton: $(basename "$d")" "$d/files/bin/wine64"
    done
    for d in "$HOME"/.local/share/lutris/runners/wine/*/; do
        [ -x "$d/bin/wine" ] && add "Lutris wine: $(basename "$d")" "$d/bin/wine"
    done
    add "other: type the path to a wine binary" ""
    WINE="$(menu "Wine to run the server with:")"
    [ -n "$WINE" ] || WINE="$(ask "path to the wine binary" "")"
fi
[ -x "$WINE" ] || die "not an executable: $WINE"
WINE="$(realpath -m "$WINE")"
# Proton's wine64 needs its own library path; the folder layout is files/lib/wine next to files/bin.
WINEDLLPATH=""
case "$WINE" in */files/bin/wine64) WINEDLLPATH="$(dirname "$(dirname "$WINE")")/lib/wine" ;; esac

# ---- 6. Wine prefix ------------------------------------------------------------
if [ -z "$PREFIX" ]; then
    LBL=(); VAL=()
    add "new dedicated prefix (recommended, the server never touches your game's prefix)" "$HOME/.local/share/rl-dedicated-server/prefix"
    [ -d "$HOME/.wine/drive_c" ] && add "existing ~/.wine" "$HOME/.wine"
    for d in "$HOME"/.local/share/Steam/steamapps/compatdata/252950/pfx; do
        [ -d "$d/drive_c" ] && add "Steam Proton prefix for Rocket League" "$d"
    done
    hp="$(json_get "$HOME/.config/heroic/GamesConfig/Sugar.json" "d.get('winePrefix')")"
    [ -n "$hp" ] && [ -d "$hp/drive_c" ] && add "Heroic prefix for Rocket League: $hp" "$hp"
    add "other: type a path (new or existing)" ""
    PREFIX="$(menu "Wine prefix:")"
    [ -n "$PREFIX" ] || PREFIX="$(ask "path to the prefix folder" "$HOME/.local/share/rl-dedicated-server/prefix")"
fi
PREFIX="$(realpath -m "$PREFIX")"
case "$PREFIX" in
    *compatdata*|*Heroic*) case "$WINE" in
        */files/bin/wine64|*/tools/*) ;;
        *) say "warning: this prefix comes from a Proton or Heroic setup; a different wine build on it may fail. Use the matching runner or the new prefix." ;;
    esac ;;
esac
if [ ! -d "$PREFIX/drive_c" ]; then
    say "creating Wine prefix at $PREFIX (first time takes a minute)"
    mkdir -p "$PREFIX"
    # First run of wine creates the prefix. "wineboot -u" hangs on a fresh prefix here (RpcSs fails), so use "cmd /c exit 0".
    # mscoree,mshtml= stops Wine from asking to download Mono and Gecko, which the server does not need.
    WINEPREFIX="$PREFIX" WINEDEBUG=-all WINEDLLOVERRIDES="mscoree,mshtml=" WINEDLLPATH="$WINEDLLPATH" \
        timeout 300 "$WINE" cmd /c exit 0 >/dev/null 2>&1 || say "warning: first Wine run exited with an error; checking the prefix"
    WINEPREFIX="$PREFIX" "$(dirname "$WINE")/wineserver" -k >/dev/null 2>&1 || true
    [ -d "$PREFIX/drive_c" ] || die "prefix not created at $PREFIX"
fi

# ---- 7. remember the choices, build -----------------------------------------------
{
    echo "GAME_DIR=$GAME"
    echo "OUT_DIR=$OUT"
    echo "MAP=$MAP"
    echo "WINE=$WINE"
    echo "WINEPREFIX=$PREFIX"
    [ -n "$WINEDLLPATH" ] && echo "WINEDLLPATH=$WINEDLLPATH"
    echo "PYTHON=$PY"
} > "$REPO/server.conf"
say "saved choices to $REPO/server.conf"
say "building the server copy (several minutes)"
(cd "$REPO" && PYTHON="$PY" ./setup.sh "$GAME" "$OUT" "$MAP")

# ---- 8. start ----------------------------------------------------------------------
ip="$(ip -4 route get 1 2>/dev/null | awk '{for (i = 1; i < NF; i++) if ($i == "src") { print $(i + 1); exit }}')"
start="$(ask "start the server now? (y/n)" "n")"
if [ "$start" = y ] || [ "$start" = Y ]; then
    name="$(ask "server name shown in the LAN browser" "Dedicated server")"
    join="$(ask "join password (blank for none)" "")"
    admin="$(ask "admin password (blank for none)" "")"
    args=(--nolog --name "$name")
    [ -n "$join" ] && args+=(--join-password "$join")
    [ -n "$admin" ] && args+=(--admin-password "$admin")
    (cd "$REPO" && ./run.sh "${args[@]}")
    say "server started, the log is in your Wine prefix (see README, Linux section)"
fi
say ""
say "done. Server copy: $OUT"
say "start:  cd $REPO && ./run.sh --name 'My server'"
say "stop:   cd $REPO && ./run.sh --stop"
[ -n "$ip" ] && say "LAN address for this PC: $ip (ports UDP 7777 and 14001)"
