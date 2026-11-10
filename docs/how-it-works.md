# How it works

For people changing the patchers. The quick guide is in the main README.

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

## Patches to the exe (`patch_exe.py`)

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

## Patches to UnrealScript (`patch_upk.py`)

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

## LAN browser (`lan_responder.py`)

The LAN browser broadcasts a `LanMessage_HostQuery_X` to UDP port 14001. It lists every `LanMessage_HostResponse_X` that echoes the query's nonce, and joins the `ServerID` address in the reply. The game's own responder (`UdpLanServer_X`) never starts on the dedicated server, so this script sends those replies instead.

Rocket League packages have an AES-encrypted header and zlib-compressed export data. `patch_upk.py` works in these steps:

1. Decrypts the header.
2. Decompresses the export data.
3. Edits the bytecode. Each edit keeps the exact original length, because export sizes must not change.
4. Recompresses only the chunks that changed.
5. Re-encrypts the header.
6. Reads the output back to check that the edits round-trip.

