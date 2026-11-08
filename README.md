# rl-dedicated

A headless Rocket League server. It runs with no window, no rendering and no sound, and it does not need the game client open.

Rocket League's normal LAN hosting runs inside the full game client. But the retail `RocketLeague.exe` also contains Psyonix's own server mode (`server <map>`, which runs `Engine.ServerCommandlet`), and it is disabled. This project patches a **private copy** of the game so that this mode boots as a LAN match. Players find it in the game's normal LAN match browser and join on UDP port 7777.

> **Status: experimental.**
> - Tested: the server boots headless and shows up in the LAN match browser, and a player on another PC joined it.
> - Not tested yet: full matches, or several players at once.
> - Tested only on the Steam build `261031.63733.533021`.

No game files are in this repo. The scripts patch the copy of the game you already own. Your real install is only read and never modified.

## Requirements

- Windows, with Rocket League installed. Only the Steam build has been tested.
- Python 3.10 or newer, plus the libraries in `requirements.txt` (`pefile` and `cryptography`).
- About 11 GB of free disk space for the server copy. Textures and audio streams are not copied.

## Setup

```powershell
git clone https://github.com/xplodingeggo/rl-dedicated
cd rl-dedicated
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
.\run.ps1 -Logs                    # also open a window that follows the server log
```

The server's own console window stays hidden. Clicking into a console window starts a text selection, and while it lasts Windows pauses writes to that console, which would freeze the server. The `-Logs` window follows the log file instead, so a selection there pauses only that window.

This starts two processes in the background, with no windows:

- the server itself
- `lan_responder.py`, which answers the game's LAN browser searches for it

To stop both:

```powershell
Stop-Process -Name RocketLeague_Server
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ? CommandLine -match lan_responder | % { Stop-Process -Id $_.ProcessId }
```

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

## Chat commands

Type these in the in-game chat while connected to the server:

| Command | Effect |
|---------|--------|
| `!map Park_P` | Runs `servertravel Park_P?game=...?Lan?listen`. Everyone is moved to the new map. |
| `!kick Name` | Runs the console command `kick Name`. |

**There is no password: every connected player can use them.** Only run the server on a network you trust. Players are not asked to confirm anything, and chat is not relayed, so players don't see each other's messages.
Commands are untested in a real match: if `!map` or `!kick` does nothing, check the server log for the console command's reply.

## Choosing the map

The map is written into `ProjectX.upk` during setup, so choosing a different map means running setup again:

```powershell
.\setup.ps1 -Game '...' -Map Park_P
.\run.ps1 -Map Park_P
```

Pass the same `-Map` to both scripts. Only `Stadium_P` has been tested.

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

The patched file is written as a new copy, `RocketLeague_Server.exe`.

| RVA | Change | Why |
|-----|--------|-----|
| `0xde2ddb`, `0xde2f68` | `jnz` to `jmp` | Server mode tries to load `OnlineSubsystemPC`, which was removed from retail builds. The patch makes it use the normal online subsystem. |
| `0xddfd7e` | `jz` to `jmp` | Skips the "Commandlets are not supported" abort. |
| `0xddd785` | jump over 0x17 bytes | The main loop calls through a global pointer that is null under `-nullrhi`, which crashes. The patch skips that call. |

### Patches to UnrealScript (`patch_upk.py`)

| Function | Change | Why |
|----------|--------|-----|
| `ProjectX`: `OnlineGameDedicatedServer_X.Inactive.BeginState` | `GoToMap("Inactive")` becomes `GoToMap("<map>?game=...?Lan?listen")` | Retail builds have no `Inactive` map. Also, the startup URL options never reach this travel, so without the patch the server never starts listening. `?Lan` makes the match a LAN match (`MatchType_Lan_TA`). |
| `ProjectX`: `OnlineGameDedicatedServerRegistration_X.SendUpdateRequest` | Jumps straight to the return | Skips registration with PsyNet, which answers `AccessDenied` for unofficial servers. |
| `ProjectX`: `GameSettingPlaylist_X.IsLanMatch` | `'LANMatch'` becomes `'PrivateMatch'` | The server downloads the `Server` playlist list, which has no `LANMatch` playlist. Without one, the match allows 0 players and every join fails with "server full". |
| `TAGame`: `GameEvent_TA.Init` | `NetMode == 2` becomes `NetMode == 1` | The LAN listen server, which accepts LAN logins, only starts for a listen server (2). A dedicated server is 1. |
| `TAGame`: `TextChatActor_TA.ServerSendMessageToPlayers` | Body replaced by the chat commands below | Lets players change the map and kick players without a console. Chat is no longer relayed between players. |

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
