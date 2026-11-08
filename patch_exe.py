"""Build the patched server exe from a stock RocketLeague.exe (the original stays untouched).
Patches are RVA-based and verified against the expected original bytes, so a game update
aborts cleanly instead of corrupting anything.

usage: python patch_exe.py <RocketLeague.exe in> <RocketLeague_Server.exe out>"""
import sys

import pefile

# (rva, expected, new, why)
PATCHES = [
    (0xde2ddb, '75', 'eb', 'online subsystem name: never pick "PC" in server mode (OnlineSubsystemPC is stripped)'),
    (0xde2f68, '75', 'eb', 'same, inlined copy'),
    (0xddfd7e, '74', 'eb', 'skip "Commandlets are not supported" abort for Engine.ServerCommandlet'),
    (0xddd785, '488b0d9c', 'eb17', 'main loop: skip call through a global (null under -nullrhi) that crashed at rva 0xddd78c'),
]

src, dst = sys.argv[1], sys.argv[2]
pe = pefile.PE(src, fast_load=True)
data = bytearray(open(src, 'rb').read())
for rva, old, new, why in PATCHES:
    off = pe.get_offset_from_rva(rva)
    o, n = bytes.fromhex(old), bytes.fromhex(new)
    assert data[off:off + len(o)] == o, f'{rva:#x}: expected {old}, found {data[off:off + len(o)].hex()} (different game build?)'
    data[off:off + len(n)] = n
    print(f'{rva:#x} {old}->{new}  {why}')
pe.close()
open(dst, 'wb').write(data)
print('wrote', dst)
