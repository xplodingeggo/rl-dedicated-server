"""Build the patched server exe from a stock RocketLeague.exe (the original stays untouched).
Every patch is verified against the expected original bytes, so a game update aborts
cleanly instead of corrupting anything.

Two patch sets are known. The first one that verifies is used:
  1. RVA-based, for the Steam build 261031.63733.533021 (the one this was first written for).
  2. Signature-based, for later builds. Each signature must match exactly once in the file.

usage: python patch_exe.py <RocketLeague.exe in> <RocketLeague_Server.exe out>"""
import re
import sys

import pefile

# Set 1: (rva, expected, new, why)
PATCHES = [
    (0xde2ddb, '75', 'eb', 'online subsystem name: never pick "PC" in server mode (OnlineSubsystemPC is stripped)'),
    (0xde2f68, '75', 'eb', 'same, inlined copy'),
    (0xddfd7e, '74', 'eb', 'skip "Commandlets are not supported" abort for Engine.ServerCommandlet'),
    (0xddd785, '488b0d9c', 'eb17', 'main loop: skip call through a global (null under -nullrhi) that crashed at rva 0xddd78c'),
]

# Set 2: (name, signature regex, offset of the patched bytes inside the match, expected bytes there, new bytes, why)
# Found on the Epic Games Store exe of the same game version (GPsyonixBuildID 261031.63733.533021).
# It compiles the online subsystem choice without branches (EOS/PC only) and has no
# "Commandlets are not supported" abort any more (the Steam workshop commandlet it guarded is gone),
# so that patch is dropped and an EOS launcher check bypass is added.
SIGNATURES = [
    ('subsystem name',
     rb'\x83\x3d....\x00\x48\x8d\x0d....\x48\x8d\x05....\x48\x0f\x44\xc1\xc3',
     21, '480f44c1', '90909090',
     'online subsystem name: "PC" if flag == 0 else "EOS"; drop the cmove so "PC" is never picked (OnlineSubsystemPC is stripped)'),
    ('subsystem name, inlined copy',
     rb'\x48\x8d\x1d....\x48\x8d\x05....\x83\x3d....\x00\x48\x0f\x45\xd8',
     21, '480f45d8', '4889c390',
     'same, inlined copy: cmovne rbx,rax becomes mov rbx,rax'),
    ('EOS launcher check',
     rb'\xe8....\x85\xc0\x74\x41\x48\x8b\x0d....\xff\x15....\x85\xc0\x75\x18\xb9\x01\x00\x00\x00\xe8....'
     rb'\xb8\x01\x00\x00\x00\x48\x83\xc4\x50\x41\x5e\x5f\x5e\xc3\x3d\xff\xff\xff\x7f\x75\x09',
     7, '7441', 'eb41',
     'skip the EOS launcher check: EOS_Platform_CheckForLauncherAndRestartIfNeeded fails (EOS_UnexpectedError) outside the Epic launcher and the server aborts with "failed to init LauncherCheck module"'),
    ('main loop call',
     rb'\x48\x8b\x0d(....)\x48\x8b\x01\x45\x33\xc9\x41\xb8\x01\x00\x00\x00\x0f\x57\xc9\xff\x50\x28',
     0, None, 'eb17',
     'main loop: skip call through a global (null under -nullrhi); 0x17 bytes jumped over end at the instruction after the call'),
]


def apply_rva_set(pe, data):
    for rva, old, new, why in PATCHES:
        off = pe.get_offset_from_rva(rva)
        o = bytes.fromhex(old)
        if data[off:off + len(o)] != o:
            return None
    out = []
    for rva, old, new, why in PATCHES:
        off = pe.get_offset_from_rva(rva)
        n = bytes.fromhex(new)
        data[off:off + len(n)] = n
        out.append(f'{rva:#x} {old}->{new}  {why}')
    return out


def apply_signature_set(pe, data):
    found = []
    for name, sig, at, old, new, why in SIGNATURES:
        hits = [m.start() for m in re.finditer(sig, bytes(data), re.S)]
        if len(hits) != 1:
            return None, f'{name}: signature matched {len(hits)} times, expected 1'
        found.append((name, hits[0] + at, old, new, why))
    out = []
    for name, off, old, new, why in found:
        n = bytes.fromhex(new)
        if old is not None:
            assert data[off:off + len(n)] == bytes.fromhex(old), f'{name}: unexpected bytes at {off:#x}'
        data[off:off + len(n)] = n
        out.append(f'{pe.get_rva_from_offset(off):#x} {data[off:off + len(n)].hex()}  [{name}] {why}')
    return out, None


src, dst = sys.argv[1], sys.argv[2]
pe = pefile.PE(src, fast_load=True)
data = bytearray(open(src, 'rb').read())
done = apply_rva_set(pe, data)
variant = 'build 261031.63733.533021 (RVA set)'
if done is None:
    data = bytearray(open(src, 'rb').read())
    done, err = apply_signature_set(pe, data)
    variant = 'signature set'
    if done is None:
        sys.exit(f'No known patch set fits this RocketLeague.exe ({err}). '
                 'Different game build: the patch sites need to be found again.')
print('using', variant)
for line in done:
    print(line)
pe.close()
open(dst, 'wb').write(data)
print('wrote', dst)
