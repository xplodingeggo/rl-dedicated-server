# rl-dedicated-server

A headless Rocket League server. It runs with no window, no rendering and no sound, and it does not need the game client open.

Rocket League's normal LAN hosting runs inside the full game client. But the retail `RocketLeague.exe` also contains Psyonix's own server mode (`server <map>`, which runs `Engine.ServerCommandlet`), and it is disabled. This project patches a **private copy** of the game so that this mode boots as a LAN match. Players find it in the game's normal LAN match browser and join on UDP port 7777.

> **Status: experimental.**
> - Tested: the server boots headless and shows up in the LAN match browser, and a player joined it. Join password, admin login, `!map` (including workshop maps), `!kick` and chat all worked.
> - Not tested yet: full matches, a wrong join password being rejected, or several players at once.
> - Tested on game build `261031.63733.533021`: the Steam exe on Windows, and both the Steam exe and the Epic Games Store exe under Wine on Linux.

No game files are in this repo. The scripts patch the copy of the game you already own. Your real install is only read and never modified.

## Requirements

- Windows, or Linux with Wine (see the Linux section), with Rocket League installed. The Steam and Epic Games Store builds have both been tested.
- Python 3.10 or newer, plus the libraries in `requirements.txt` (`pefile` and `cryptography`).
- About 11 GB of free disk space for the server copy. Textures and audio streams are not copied.

## Quick install

The installer asks a few questions and does the rest. Paste one line:

Linux (Wine), in a terminal:
```bash
curl -fsSL https://raw.githubusercontent.com/xplodingeggo/rl-dedicated-server/main/install.sh | bash
```

Windows, in PowerShell:
```powershell
irm https://raw.githubusercontent.com/xplodingeggo/rl-dedicated-server/main/install.ps1 | iex
```

It asks, with autodetected choices listed first:
1. Where to keep the repo (default `~/rl-dedicated-server`, or `%USERPROFILE%\rl-dedicated-server`).
2. Your Rocket League folder. Steam libraries and Epic (through Heroic on Linux) are found automatically. Pick "other" to type a path. The game folder is only read.
3. Where to put the server copy (about 11 GB).
4. Linux only: which Wine to use. The list shows system Wine, Proton and GE-Proton from Steam, Heroic and Lutris builds, and "other" for a custom path.
5. Linux only: which Wine prefix to use. The default is a new prefix just for the server (`~/.local/share/rl-dedicated-server/prefix`), so it never touches your game's prefix. Existing prefixes from `~/.wine`, Steam (Proton) and Heroic are listed too. Pick "other" for any other path.
6. Whether to start the server, with optional server name, join password and admin password.

The answers are saved in `server.conf` in the repo. `run.sh` and `run.ps1` read it, so later runs use the same Wine and prefix. Command-line options and environment variables still override it.

Options for the Linux installer, to skip questions: `--repo DIR --game DIR --out DIR --wine PATH --prefix DIR --yes` (`--yes` takes the first choice for anything not given).

Status of the installer:
- `install.sh` (Linux): tested end to end with the Epic Games Store install under system Wine, a new prefix and a non-interactive run. Pasting the `curl` line itself is tested once the repo is pushed.
- `install.ps1` (Windows): not run yet. Use the manual steps below if it fails and report what happened.

## Setup

```powershell
git clone https://github.com/xplodingeggo/rl-dedicated-server
cd rl-dedicated-server
python -m pip install -r requirements.txt
.\setup.ps1 -Game 'C:\Program Files (x86)\Steam\steamapps\common\rocketleague'
```

`setup.ps1` does the following:

1. Copies the parts of the game the server needs into `.\game`. To use another folder, pass `-Out D:\somewhere`.
2. Writes patched `ProjectX.upk` and `TAGame.upk` files into the copy, using `patch_upk.py`.
3. Writes a patched `RocketLeague_Server.exe` into the copy, using `patch_exe.py`.

If PowerShell blocks the scripts, run them as `powershell -ExecutionPolicy Bypass -File .\setup.ps1 ...`.

**Run setup again after every game update.** Both patchers check the original bytes before they change anything. If a game update moved the code, they stop with an error and write nothing broken.

## Running

```powershell
.\run.ps1                          # uses .\game
.\run.ps1 -Dir D:\somewhere        # if you used -Out during setup
.\run.ps1 -Name 'Friday league'    # the name shown in the LAN browser
.\run.ps1 -NoLog                   # do not open the window that follows the server log (it opens by default)
```

The server's own console window stays hidden. Clicking into a console window starts a text selection, and while it lasts Windows pauses writes to that console, which would freeze the server. The log window follows the log file instead, so a selection there pauses only that window.

This starts two processes in the background, with no windows:

- the server itself
- `lan_responder.py`, which answers the game's LAN browser searches for it

To stop everything (the server, the LAN responder and the log windows):

```powershell
.\stop.ps1
```

## Linux

**Tested** under Wine 11 with both the Epic Games Store build and the Steam build: the server reaches `Stadium_P`, listens on UDP 7777, and a game client on the same PC joined it, used the join password and admin login, and changed maps with `!map`. The patchers are plain Python and run on Linux. The server itself is a Windows exe, so it runs under Wine. `setup.sh` and `run.sh` do what `setup.ps1` and `run.ps1` do:

```bash
python3 -m pip install -r requirements.txt
./setup.sh ~/.local/share/Steam/steamapps/common/rocketleague   # the Windows game files, as installed by Steam or Epic (Heroic)
./run.sh --name 'Friday league' --join-password letmein --admin-password s3cret
./run.sh --stop
```

- `run.sh` takes the same options as `run.ps1`: `--dir`, `--map`, `--name`, `--extra`, `--join-password`, `--admin-password`, `--nolog`.
- You need `wine` and Python 3.10 or newer. `mapurl.py` also needs tkinter (`python3-tk` on Debian and Ubuntu).
- Wine uses `~/.wine` unless you set `WINEPREFIX`. Set it to Steam's Proton prefix to reuse that one: `WINEPREFIX=~/.local/share/Steam/steamapps/compatdata/252950/pfx ./run.sh`.
- The server log is in the prefix: `$WINEPREFIX/drive_c/users/<user>/Documents/My Games/Rocket League/TAGame/Logs/`. By default `run.sh` follows it with `tail -F` and stays in the foreground (Ctrl+C stops only the tail; the server keeps running). `--nolog` skips that.
- Open UDP ports 7777 and 14001 in your firewall for the PC running the server.
- The log fills with `NotLoggedInToPsynet` and EOS overlay errors. They are harmless: the server does not log in to PsyNet or Epic.
- The first start takes about 40 seconds before it listens (the hardware survey runs for about 30 of them under Wine).
- File names are matched ignoring case (`fs.py`, and `ci` in `setup.sh`), so a Steam install with different capitalisation still works. Wine itself looks files up ignoring case; a folder holding two files that differ only by case is not handled.

## Joining

1. In Rocket League, open the LAN match browser.
2. Click the server. Its name is "Dedicated server" unless you passed `-Name`.
3. Wait a few seconds. Clicking again cancels the attempt in progress.

Players can join from the PC that runs the server, or from any PC on the same network. Windows asks to allow `RocketLeague_Server.exe` and Python through the firewall the first time; allow both on private networks.

To accept players from outside your network, forward UDP port 7777 on your router. They can't see the server in their LAN browser, though, so they need another way to connect. That part is untested.

**Logs** are written to `Documents\My Games\Rocket League\TAGame\Logs\Launch.log`. If the game client is also open, the client keeps `Launch.log` and the server writes `Launch_2.log` instead. A healthy start contains these lines:

```
Log: Game class is 'GameInfo_Soccar_TA'
DevNet: TcpNetDriver_0 TcpNetDriver listening on port 7777
Log: Bringing World Stadium_P.TheWorld up for play
```

## Passwords

Both are optional launch options of `run.ps1`:

```powershell
.\run.ps1 -JoinPassword letmein -AdminPassword s3cret
```

- `-JoinPassword`: players must enter it to join. The LAN browser shows the server as password protected.
- `-AdminPassword`: a player becomes an admin by typing `!admin s3cret` in chat. The message is relayed as `!admin ****`, so the other players never see the password. Admins get the match admin menu and can use the chat commands below. Without `-AdminPassword` nobody is an admin.

Passwords cannot contain spaces or quotes. They are passed on the server's command line, so any user on the PC running the server can read them in the process list. They travel unencrypted over the network, so use them on a network you trust. Admin status lasts until the player disconnects or the map changes; type `!admin` again after a `!map`.

## Chat commands

Admins can type these in the in-game chat:

| Command | Effect |
|---------|--------|
| `!map Park_P` | Runs `servertravel Park_P?game=...?Lan?listen`. Everyone is moved to the new map. |
| `!kick Name` | Kicks the player whose in-game name is `Name` (not case sensitive). |

Other players' commands are ignored. The command message is relayed to the other players like any other chat.

Every chat message is also written to the server log as `Chat <player>: <text>`, so the log window shows the chat. The server runs with `-forcelogflush`, so lines appear right away. The password in an `!admin` login is masked in the log too.

### Map line generator

`python mapurl.py` opens a window where you pick the map and the game settings (game mode such as Dropshot or Heatseeker, match length, max score, ball type, gravity, boost, rumble and the rest of the mutators, bots, skip replays) from a list and dropdowns. It builds the `!map ...` line, like `!map Park_P?GameTags=10Minutes,Ball_Puck?NumBots=3`; press Copy and paste it in the game chat. Pass `--game <folder>` if the server copy is not in `.\game`. The settings and their game tags are the ones Rocket Plugin uses (`mutators.py`). The game limits chat messages to 120 characters, so the window warns when a line is too long. The game mode and mutator options have not been tested in a real match yet.

**Untested:** the server reading `GameTags`, `NumBots` and `noreplay` from the `!map` line. If a setting has no effect in a match, tell me which one.

## Choosing the map

The starting map is written into `ProjectX.upk` during setup, so it is chosen at setup time. The installer asks for it, and it is saved as `MAP=` in `server.conf`. The default is `Stadium_P`.

To change it later, run setup again with the new map:

```bash
./setup.sh ~/.local/share/Steam/steamapps/common/rocketleague ./game Park_P   # Linux
```
```powershell
.\setup.ps1 -Game '...' -Map Park_P                                          # Windows
```

Then set `MAP=Park_P` in `server.conf` (or pass `-Map` / `--map` to run.ps1 / run.sh). `run.sh` and `run.ps1` warn when the copy was set up for a different map. Only `Stadium_P` has been tested as the starting map.

## How it works

The server is started like this:

```
RocketLeague_Server.exe server Stadium_P?game=TAGame.GameInfo_Soccar_TA?Lan?listen -FakeServer -noeac -nullrhi -nosound -unattended
```

What the launch flags do:

| Flag | Purpose |
|------|---------|
| `-nullrhi`, `-nosound` | Run with no renderer and no audio. |
| `-noeac` | Skip Easy Anti-Cheat. |
| `-FakeServer` | Psyonix's own development switch. It skips the matchmaking reservation check. |

### Patches to the exe (`patch_exe.py`)

The patched file is written as a new copy, `RocketLeague_Server.exe`. Every patch is checked against the expected original bytes first. `patch_exe.py` knows two patch sets and uses the first that verifies.

**Steam exe (fixed addresses):**

| RVA | Change | Why |
|-----|--------|-----|
| `0xde2ddb`, `0xde2f68` | `jnz` to `jmp` | Server mode tries to load `OnlineSubsystemPC`, which was removed from retail builds. The patch makes it use the normal online subsystem. |
| `0xddfd7e` | `jz` to `jmp` | Skips the "Commandlets are not supported" abort. |
| `0xddd785` | jump over 0x17 bytes | The main loop calls through a global pointer that is null under `-nullrhi`, which crashes. The patch skips that call. |

**Epic Games Store exe (found by byte pattern, each pattern must match exactly once):**

| Patch | Why |
|-------|-----|
| Two `cmove`/`cmovne` instructions that choose the online subsystem name become a no-op and a plain `mov` | This exe picks `PC` or `EOS` without a branch. The patch always picks `EOS` instead of the stripped `PC`. |
| `je` to `jmp` after the check that calls `EOS_Platform_CheckForLauncherAndRestartIfNeeded` | Outside the Epic launcher the check fails with `EOS_UnexpectedError` and the server aborts with "failed to init LauncherCheck module". |
| Jump over the main loop's call through a null global (same patch as for Steam) | Same crash under `-nullrhi`. |

The "Commandlets are not supported" abort is not in the Epic exe (the Steam workshop commandlet it guarded was removed), so it needs no patch there.

### Patches to UnrealScript (`patch_upk.py`)

| Function | Change | Why |
|----------|--------|-----|
| `ProjectX`: `OnlineGameDedicatedServer_X.Inactive.BeginState` | `GoToMap("Inactive")` becomes `GoToMap("<map>?game=...?Lan?listen")` | Retail builds have no `Inactive` map. Also, the startup URL options never reach this travel, so without the patch the server never starts listening. `?Lan` makes the match a LAN match (`MatchType_Lan_TA`). |
| `ProjectX`: `OnlineGameDedicatedServerRegistration_X.SendUpdateRequest` | Jumps straight to the return | Skips registration with PsyNet, which answers `AccessDenied` for unofficial servers. |
| `ProjectX`: `GameSettingPlaylist_X.IsLanMatch` | `'LANMatch'` becomes `'PrivateMatch'` | The server downloads the `Server` playlist list, which has no `LANMatch` playlist. Without one, the match allows 0 players and every join fails with "server full". |
| `TAGame`: `GameEvent_TA.Init` | `NetMode == 2` becomes `NetMode == 1` | The LAN listen server, which accepts LAN logins, only starts for a listen server (2). A dedicated server is 1. |
| `TAGame`: `TextChatActor_TA.ServerSendMessageToPlayers` | The two guard statements at the top become a call to `GFxData_Products_TA.UpdateProductData` | Hands each chat message to the command parser. The chat relay itself is untouched. |
| `TAGame`: `GFxData_Products_TA.UpdateProductData` | Body replaced by the command parser | A large menu function a server never runs, so its body is free. Handles `!admin <password>` (and hides the password from the relay), `!map` and `!kick`. |
| `TAGame`: `TextChatActor_TA.SendSignedMessage` | Body replaced by a loop over `WorldInfo.AllControllers` | Client-only as well. Calls `KickPlayerForReason` on the player whose name matches. |
| `TAGame`: `ListenServer_TA.GetCustomMatchSettings` | Body replaced by a read of `-JoinPassword=` into the returned settings | The game's own login check (`AllowPlayerLogin`) then rejects players whose password differs. |
| `TAGame`: `MatchAdminComponent_TA.IsMatchAdmin` | Body replaced by `return PRI.bMatchAdmin` | Only players who logged in with `!admin` keep the match admin menu. |

### LAN browser (`lan_responder.py`)

The LAN browser broadcasts a `LanMessage_HostQuery_X` to UDP port 14001. It lists every `LanMessage_HostResponse_X` that echoes the query's nonce, and joins the `ServerID` address in the reply. The game's own responder (`UdpLanServer_X`) never starts on the dedicated server, so this script sends those replies instead.

Rocket League packages have an AES-encrypted header and zlib-compressed export data. `patch_upk.py` works in these steps:

1. Decrypts the header.
2. Decompresses the export data.
3. Edits the bytecode. Each edit keeps the exact original length, because export sizes must not change.
4. Recompresses only the chunks that changed.
5. Re-encrypts the header.
6. Reads the output back to check that the edits round-trip.

## Known issues

- When the server crashes, it may upload a crash report to Psyonix. The game's `PsyNetConfig.bAllowBacktraceUploads` setting controls this.
- The server and the client share one log folder, so a client started later can overwrite the server's log.
- Firewall rules that block `RocketLeague.exe` from reaching the server PC make joining fail silently: the game shows nothing and the server logs nothing.

## Disclaimer

This project is not affiliated with or endorsed by Psyonix or Epic Games. Run modified game binaries at your own risk.

## License

MIT. See [LICENSE](LICENSE).
