# rl-dedicated-server

A headless Rocket League server: no window, no rendering, no sound. Players find it in the normal LAN match browser and join on UDP port 7777.

It patches a **private copy** of the game you already own. Your install is only read, never changed.

**Status:** experimental. Tested on the Steam and Epic builds (game build `261031.63733.533021`), on Windows and on Linux under Wine. Joining, passwords, admin, `!map` and `!kick` work. Not yet tested: full matches, several players, and joining from the Windows installer.

## Install

Needs Rocket League installed, 11 GB free, and Python 3.10+.

**Linux (Wine)**, paste in a terminal:
```bash
curl -fsSL https://raw.githubusercontent.com/xplodingeggo/rl-dedicated-server/main/install.sh | bash
```

**Windows**, paste in PowerShell:
```powershell
irm https://raw.githubusercontent.com/xplodingeggo/rl-dedicated-server/main/install.ps1 | iex
```

The installer asks where your game is, where to put the server copy, the starting map (default `Stadium_P`), and on Linux which Wine and prefix to use. Answers are saved to `server.conf`. Run it again after every game update.

Skip the questions on Linux with `--game DIR --out DIR --map NAME --wine PATH --prefix DIR --yes`.

## Run and stop

```bash
./run.sh --name 'Friday league' --join-password letmein --admin-password s3cret
./run.sh --stop
```
```powershell
.\run.ps1 -Name 'Friday league' -JoinPassword letmein -AdminPassword s3cret
.\stop.ps1
```

Both take `--nolog` / `-NoLog` to skip the log window. Passwords can't contain spaces or quotes. They are visible in the process list and sent unencrypted, so use them on a network you trust.

Open UDP 7777 and 14001 in the firewall of the server PC.

## Launch arguments

`run.sh` and `run.ps1` start the server with these defaults. Most people never need to change them:

| Default flag | What it does |
|--------------|--------------|
| `-FakeServer` | Psyonix's own development switch. Skips the matchmaking reservation check. |
| `-noeac` | Skips Easy Anti-Cheat. |
| `-nullrhi` | Runs with no renderer. |
| `-nosound` | Runs with no audio. |
| `-unattended` | No dialogs or prompts, so the server never waits for input. |
| `-nostartupmovies` | Skips the intro movies. |

To replace the defaults, pass your own flags with `--launch` (`bash`) or `-Launch` (PowerShell). For example, `./run.sh --launch '-noeac -nosound'` keeps only those two. `--launch ''` drops all the defaults.

These are always added and can't be turned off, because the log window and the password checks depend on them:

| Always added | What it does |
|--------------|--------------|
| `server <map>?game=TAGame.GameInfo_Soccar_TA?Lan?listen` | Starts the server on `<map>` in standard soccar, as a LAN listen server. |
| `-log` | Writes the log to `Launch.log`. |
| `-forcelogflush` | Flushes the log after every line, so log windows update at once. |
| `-JoinPassword=<pw>` | Added with `--join-password` / `-JoinPassword`. Players must enter this password to join. |
| `-AdminPassword=<pw>` | Added with `--admin-password` / `-AdminPassword`. Enables `!admin <pw>` in chat. |

## Join

Open the LAN match browser, click the server, wait a few seconds. Clicking again cancels.

## Admin and chat commands

Type `!admin <admin password>` in chat. Admin status lasts until you disconnect or the map changes, so type it again after `!map`.

| Command | Effect |
|---------|--------|
| `!map Park_P` | Moves everyone to that map. |
| `!kick Name` | Kicks that player. |

Other players' commands are ignored. The password is shown as `****` in chat and in the log.

## Map

The starting map is baked into the server copy at setup, so change it by setting up again. Set `MAP=` in `server.conf` to match, or pass `--map` / `-Map` to run. The run script warns when they differ. Only `Stadium_P` has been tested as a starting map.

## Logs

- Linux: the log is in your Wine prefix under `drive_c/users/<user>/Documents/My Games/Rocket League/TAGame/Logs/`.
- Windows: `Documents\My Games\Rocket League\TAGame\Logs\`.

A healthy start ends with `TcpNetDriver listening on port 7777` and `Bringing World Stadium_P`. The `NotLoggedInToPsynet` and EOS overlay errors are harmless.

## Known issues

- The first start takes about 40 seconds.
- A game client started on the same PC can overwrite the server's `Launch.log`. The server then writes `Launch_2.log`.
- Map chat commands and `GameTags`/`NumBots` from the `!map` line are only partly tested.

## More

- Patch details and how the LAN browser works: [docs/how-it-works.md](docs/how-it-works.md)
- Game updates: patchers check the original bytes and stop with an error if the game changed, so setup again.
- `python mapurl.py` builds `!map` lines with game mode and mutator options.

## Disclaimer

Not affiliated with or endorsed by Psyonix or Epic Games. Run modified game binaries at your own risk.

## License

MIT. See [LICENSE](LICENSE).
