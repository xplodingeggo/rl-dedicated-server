"""Patch ProjectX.upk for the dedicated server.

Two length-neutral UnrealScript bytecode edits (export sizes must not change):
  * OnlineGameDedicatedServer_X.Inactive.BeginState: GoToMap("Inactive") -> GoToMap(<listen URL>).
    Retail has no Inactive map, and the startup URL options never reach the travel URL.
    Room comes from shortening an unused log string; the one jump over it is retargeted.
  * OnlineGameDedicatedServerRegistration_X.SendUpdateRequest: skip PsyNet CreateGameServer/UpdateGameServer
    (Psyonix answers AccessDenied). JumpIfNot -> Jump to the final return keeps the token stream valid.

Rocket League packages: header tables are AES-256 encrypted (ECB, or CTR with a nonce on newer builds),
export data lives in zlib-compressed chunks. Only the touched chunks are recompressed; the chunk table
in the header is updated and the header re-encrypted, so the file keeps its original framing.

Plus edits in TAGame.upk:
  * GameEvent_TA.Init: start the LAN listen server (LAN browser responder) on a dedicated server too.
  * Chat commands, the `!admin <password>` login and the -JoinPassword / -AdminPassword command line options (see chat_hook).

usage: python patch_upk.py <CookedPCConsole in> <CookedPCConsole out> [map]
"""
import struct
import sys
import zlib

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MAGIC = 0x9E2A83C1
FLAG_CTR = 0x0800
# Rocket League's package key (public; the same one every RL package tool ships).
KEY = bytes([199, 223, 107, 19, 37, 42, 204, 113, 71, 187, 81, 201, 138, 215, 227, 75,
             127, 229, 0, 183, 127, 165, 250, 178, 147, 226, 242, 78, 107, 23, 231, 121])
URL = '{}?game=TAGame.GameInfo_Soccar_TA?Lan?listen'  # ?Lan -> MatchType_Lan_TA, so the LAN browser can list it


def i32(b, o): return struct.unpack_from('<i', b, o)[0]
def i64(b, o): return struct.unpack_from('<q', b, o)[0]


def skip_fstring(b, o):
    n = i32(b, o)
    return o + 4 + (n if n >= 0 else -n * 2)


def fstring(b, o):
    n = i32(b, o)
    if n >= 0:
        return b[o + 4:o + 4 + n].rstrip(b'\0').decode('latin-1'), o + 4 + n
    return b[o + 4:o + 4 - n * 2].decode('utf-16-le').rstrip('\0'), o + 4 - n * 2


def aes(data, nonce, encrypt):
    if nonce is not None:  # CTR: nonce + 32-bit big-endian block counter from 0
        c = Cipher(algorithms.AES(KEY), modes.CTR(nonce + b'\0\0\0\0'))
    else:
        c = Cipher(algorithms.AES(KEY), modes.ECB())
    x = c.encryptor() if encrypt else c.decryptor()
    return x.update(bytes(data)) + x.finalize()


def read_header(raw):
    assert i32(raw, 0) & 0xFFFFFFFF == MAGIC, 'not a UPK'
    h = {}
    h['fv'], h['lv'] = struct.unpack_from('<HH', raw, 4)
    h['total'] = i32(raw, 8)
    o = skip_fstring(raw, 12)
    h['flags'] = i32(raw, o) & 0xFFFFFFFF
    h['name_count'], h['name_off'], h['exp_count'], h['exp_off'] = struct.unpack_from('<4i', raw, o + 4)
    o += 4 + 6 * 4 + 4 + 4 * 4 + 16          # flags, 6 table fields, depends, 4 guid/thumbnail fields, guid
    o += 4 + i32(raw, o) * 12                 # generations
    o += 12                                   # engine, cooker, compression flags
    o += 4 + i32(raw, o) * 16                 # compressed chunks (empty in RL)
    o += 4
    n = i32(raw, o); o += 4
    for _ in range(n):
        o = skip_fstring(raw, o)              # additional packages to cook
    n = i32(raw, o); o += 4
    for _ in range(n):
        o += 20; o += 4 + i32(raw, o) * 4     # texture allocations
    h['gap'], h['chunk_table'], h['last_block'] = struct.unpack_from('<3i', raw, o)
    h['nonce'] = raw[o + 12:o + 24] if h['lv'] >= 33 else None
    ctr = h['flags'] & FLAG_CTR
    size = h['total'] - (h['last_block'] if ctr else h['gap']) - h['name_off']
    h['enc_size'] = size if ctr else (size + 15) & ~15
    return h


def parse_chunks(dec, h):
    wide = h['lv'] >= 22
    os_ = 8 if wide else 4
    normal = os_ + 4 + os_ + 4
    off = (lambda o: i64(dec, o)) if wide else (lambda o: i32(dec, o))
    count = i32(dec, h['chunk_table'])
    assert 0 < count < 1000, f'implausible chunk count {count} (wrong key?)'
    first = h['chunk_table'] + 4
    stride = normal + 12 if h['lv'] >= 33 else normal
    if count >= 2 and h['lv'] < 33 and off(first + normal + 12) == off(first) + i32(dec, first + os_):
        stride = normal + 12
    chunks = []
    for i in range(count):
        e = first + i * stride
        chunks.append(dict(uo=off(e), us=i32(dec, e + os_), co=off(e + os_ + 4), cs=i32(dec, e + os_ + 4 + os_),
                           entry=e, nonce=dec[e + normal:e + normal + 12] if h['lv'] >= 33 else None))
    return chunks, os_, wide


def decompress(b, o):
    magic, bs, _, usize = struct.unpack_from('<4I', b, o)
    assert magic == MAGIC, 'bad chunk'
    n = (usize + bs - 1) // bs
    sizes = [struct.unpack_from('<2I', b, o + 16 + i * 8) for i in range(n)]
    p = o + 16 + n * 8
    out = bytearray()
    for cs, _ in sizes:
        out += zlib.decompress(b[p:p + cs]); p += cs
    return out, bs, p - o


def compress(payload, bs):
    blocks = [zlib.compress(bytes(payload[i:i + bs]), 9) for i in range(0, len(payload), bs)]
    out = struct.pack('<4I', MAGIC, bs, sum(map(len, blocks)), len(payload))
    out += b''.join(struct.pack('<2I', len(c), min(bs, len(payload) - i * bs)) for i, c in enumerate(blocks))
    return out + b''.join(blocks)


class Package:
    def __init__(self, raw):
        self.raw = raw
        h = self.h = read_header(raw)
        self.ctr_nonce = h['nonce'] if h['flags'] & FLAG_CTR else None
        self.dec = bytearray(aes(raw[h['name_off']:h['name_off'] + h['enc_size']], self.ctr_nonce, False))
        n = i32(self.dec, 0)
        assert 0 < n <= 512 and self.dec[4 + n - 1] == 0, 'header did not decrypt (unknown key)'
        self.chunks, self.os, self.wide = parse_chunks(self.dec, h)
        size = len(raw)
        datas = []
        for c in self.chunks:
            if self.ctr_nonce is not None:
                data, c['bs'], _ = decompress(aes(raw[c['co']:c['co'] + c['cs']], c['nonce'], False), 0)
                c['phys'] = c['cs']
            else:
                data, c['bs'], c['phys'] = decompress(raw, c['co'])
            datas.append(data)
            size = max(size, c['uo'] + len(data))
        img = self.img = bytearray(size)
        img[:len(raw)] = raw
        img[h['name_off']:h['name_off'] + len(self.dec)] = self.dec
        for c, data in zip(self.chunks, datas):
            img[c['uo']:c['uo'] + len(data)] = data
        o = h['name_off']
        self.names = []
        for _ in range(h['name_count']):
            s, o = fstring(img, o)
            self.names.append(s); o += 8
        o = h['exp_off']
        self.exports = []
        for _ in range(h['exp_count']):
            name = self.names[i32(img, o + 12)]
            outer = i32(img, o + 8)
            o += 4 * 3 + (8 if h['fv'] >= 343 else 4) + 4 + 8
            size = i32(img, o); o += 4
            offset = i64(img, o) if h['lv'] >= 22 else i32(img, o); o += 8 if h['lv'] >= 22 else 4
            o += 4; o += 4 + i32(img, o) * 4; o += 16 + 4
            self.exports.append((name, outer, offset, size))
        self.modified = set()

    def path(self, i):
        name, outer, _, _ = self.exports[i]
        return name if outer <= 0 else self.path(outer - 1) + '.' + name

    def export(self, path):
        hits = [i for i, e in enumerate(self.exports) if e[0] == path.rsplit('.', 1)[-1] and self.path(i) == path]
        assert len(hits) == 1, f'{path}: {len(hits)} matches'
        _, _, off, size = self.exports[hits[0]]
        return off, size

    def write(self, off, data):
        first = min(c['uo'] for c in self.chunks)
        assert off >= first, 'edit lands in the header region'
        for i, c in enumerate(self.chunks):
            end = max(self.chunks[i + 1]['uo'] if i + 1 < len(self.chunks) else 0, c['uo'] + c['us'])
            if c['uo'] <= off < end:
                assert off + len(data) <= end, 'edit spans two chunks'
                self.modified.add(i)
                self.img[off:off + len(data)] = data
                return
        raise AssertionError('edit outside compressed data')

    def repack(self):
        h, raw = self.h, self.raw
        out = bytearray()
        cursor = 0
        offsets, sizes = {}, {}
        for i in sorted(range(len(self.chunks)), key=lambda i: self.chunks[i]['co']):
            c = self.chunks[i]
            out += raw[cursor:c['co']]
            offsets[i] = len(out)
            if i in self.modified:
                nxt = self.chunks[i + 1]['uo'] - c['uo'] if i + 1 < len(self.chunks) else 0
                packed = compress(self.img[c['uo']:c['uo'] + max(nxt, c['us'])], c['bs'])
                if self.ctr_nonce is not None:
                    packed = aes(packed, c['nonce'], True)
                out += packed
            else:
                out += raw[c['co']:c['co'] + c['phys']]
            sizes[i] = len(out) - offsets[i]
            cursor = c['co'] + c['phys']
        out += raw[cursor:]
        dec = bytearray(self.dec)
        for i, c in enumerate(self.chunks):
            f = c['entry'] + self.os + 4
            struct.pack_into('<qi' if self.wide else '<ii', dec, f, offsets[i], sizes[i])
        out[h['name_off']:h['name_off'] + h['enc_size']] = aes(dec, self.ctr_nonce, True)
        return bytes(out)


def lit(s):
    return b'\x1f' + s.encode() + b'\x00'


def projectx_edits(pkg, url):
    off, size = pkg.export('OnlineGameDedicatedServer_X.Inactive.BeginState')
    b = bytearray(pkg.img[off:off + size])
    old_log = lit('bQueuedShutdown while entering InActive state, so just quit')
    old_map, new_map = lit('Inactive'), lit(url)
    assert b.count(old_log) == 1 and b.count(old_map) == 1, 'BeginState not as expected (already patched or game updated)'
    room = len(old_log) + len(old_map) - len(new_map) - 2
    assert room >= 0, f'map URL too long by {-room} bytes'
    new_log = lit('q' * room)
    shrink = len(old_log) - len(new_log)
    assert b[0x30:0x33] == b'\x07\x98\x00', 'BeginState jump not as expected'
    b[0x31] -= shrink
    b = b.replace(old_log, new_log).replace(old_map, new_map)
    assert len(b) == size
    yield off, bytes(b)

    off, size = pkg.export('OnlineGameDedicatedServerRegistration_X.SendUpdateRequest')
    b = bytearray(pkg.img[off:off + size])
    assert b[0x30:0x33] == b'\x07\x33\x00', 'SendUpdateRequest not as expected (already patched or game updated)'
    b[0x30:0x33] = b'\x06\x3d\x00'
    yield off, bytes(b)

    # GameSettingPlaylist_X.IsLanMatch: Name == 'LANMatch' -> Name == 'PrivateMatch'. The server downloads the
    # "Server" playlist config, which has no LANMatch, so MatchType_Lan_TA found no playlist and the match had
    # 0 max players ("server full"). A NameConst is a fixed-size name index, so this stays length-neutral.
    off, size = pkg.export('GameSettingPlaylist_X.IsLanMatch')
    b = bytearray(pkg.img[off:off + size])
    old = b'\x21' + struct.pack('<i', pkg.names.index('LANMatch'))
    assert b.count(old) == 1, 'IsLanMatch not as expected (already patched or game updated)'
    yield off, bytes(b.replace(old, b'\x21' + struct.pack('<i', pkg.names.index('PrivateMatch'))))


def tagame_edits(pkg, url):
    # GameEvent_TA.Init: `if (IsPlayingLan() && NetMode == NM_ListenServer) InitListenServer()`.
    # A dedicated server is NM_DedicatedServer (1); without this it never answers LAN browser searches.
    off, size = pkg.export('GameEvent_TA.Init')
    b = bytearray(pkg.img[off:off + size])
    old = b'\x38\x3a\x24\x02\x16\x16'   # int(byte 2) ) )
    assert b.count(old) == 1, 'GameEvent_TA.Init not as expected (already patched or game updated)'
    b = b.replace(old, b'\x38\x3a\x24\x01\x16\x16')
    yield off, bytes(b)

    yield from chat_hook(pkg, url)

    yield from password_edits(pkg)

    # MatchAdminComponent_TA.IsMatchAdmin(PRI) normally says yes only for the match owner, which a dedicated server lacks.
    # It now returns PRI.bMatchAdmin: UpdatePlayer keeps whatever the `!admin <password>` chat login set with SetMatchAdmin.
    off, size = pkg.export('MatchAdminComponent_TA.IsMatchAdmin')
    b = bytearray(pkg.img[off:off + size])
    code_len = i32(b, 0x2c)
    assert b[0x30:0x32] == b'\x07\x35' and b[0x30 + code_len - 1] == 0x4c, 'IsMatchAdmin not as expected (already patched or game updated)'
    out = E(b'\x04\x5e\x19\x00\x2b', Ref(48581), b'\x09\x00', Ref(57518), b'\x00\x01', Ref(57518))   # return PRI.bMatchAdmin
    pad = code_len - 1 - len(out[0])
    struct.pack_into('<i', b, 0x28, mem(out) + pad + 1)
    b[0x30:0x30 + code_len] = out[0] + b'\x0b' * pad + b'\x4c'
    yield off, bytes(b)


class Ref(int):
    """A reference to an object, name or property: 4 bytes serialized, 8 in memory."""


def E(*parts):
    """Join bytes, Refs and (bytes, refs) pieces -> (bytes, number of references)."""
    data, refs = b'', 0
    for x in parts:
        if isinstance(x, Ref):
            data += struct.pack('<i', x); refs += 1
        elif isinstance(x, tuple):
            data += x[0]; refs += x[1]
        else:
            data += x
    return data, refs


def mem(t): return len(t[0]) + 4 * t[1]   # size in memory, which is what jump targets and Context skips count


def ctxm(local, member):   # local.member
    return E(b'\x19\x00\x2b', Ref(local), b'\x09\x00', Ref(member), b'\x00\x01', Ref(member))


def parse_arg(key, out):   # EngineShare_X.ParseCommandlineString(key, out): the value of -key=value on the command line
    inner = E(b'\x1c', Ref(-2591), lit(key), out, b'\x48\x16')
    return E(b'\x5e\x12\x00\x20', Ref(-1041), struct.pack('<H', mem(inner)), Ref(-371), b'\x00', inner)


def assemble(items):
    """items: ('stmt', piece) | ('jn', label, cond) = if (!cond) goto label | ('j', label) | ('lbl', name) -> (bytes, refs)"""
    sizes = {'stmt': lambda i: mem(i[1]), 'jn': lambda i: 3 + mem(i[2]), 'j': lambda i: 3, 'lbl': lambda i: 0}
    labels, at = {}, 0
    for i in items:
        if i[0] == 'lbl':
            labels[i[1]] = at
        at += sizes[i[0]](i)
    parts = []
    for i in items:
        if i[0] == 'stmt':
            parts.append(i[1])
        elif i[0] == 'jn':
            parts += [b'\x07' + struct.pack('<H', labels[i[1]]), i[2]]
        elif i[0] == 'j':
            parts.append(b'\x06' + struct.pack('<H', labels[i[1]]))
    return E(*parts)


def chat_hook(pkg, url):
    # Chat commands and the admin login. The relay in TextChatActor_TA.ServerSendMessageToPlayers stays intact; its two
    # leading guard statements (client check, sanity check) are replaced by a call to H(Staged.MessageObject), where H is
    # GFxData_Products_TA.UpdateProductData: a large menu function a server never runs, so its body is free. It runs on the
    # chat actor of the player who sent the message, and its body is the parser:
    #   if (Left(text, 7) ~= "!admin ") {                       -- everyone may try this
    #       if (-AdminPassword=<pw> was given && Mid(text, 7, 255) == pw) OwnerPC.PlayerReplicationInfo.SetMatchAdmin(true);
    #       text = "!admin ****";                               -- the relay below would show the password to everyone
    #   } else if (OwnerPC.PlayerReplicationInfo.bMatchAdmin) {
    #       if (Left(text, 5) ~= "!map ") ConsoleCommand("servertravel " $ Mid(text, 5, 255) $ "<url options>");
    #       if (Left(text, 6) ~= "!kick ") SendSignedMessage(Mid(text, 6, 255));    -- its body is the kick loop below
    #   }
    #   Log("Chat <name>: " $ text);
    # Jump targets and Context skips are memory sizes, where every 4-byte reference takes 8 bytes. The call replacing the
    # guards keeps the old memory size (padded with harmless statements), so no other offset in the function moves.
    H, P, SAN = Ref(38976), 38975, 38947   # H and its parameter (the message object) and its string local
    off, size = pkg.export('TextChatActor_TA.ServerSendMessageToPlayers')
    b = bytearray(pkg.img[off:off + size])
    tail = bytes.fromhex('040b 0f5e1900 01b3140100 0900 9ef9')    # end of the second guard, start of the relay
    head, old_mem = 0x30, 156
    assert b.count(tail) == 1 and b[head:head + 3] == b'\x07\x16\x00' and b[head + 18:head + 21] == b'\x07\x9c\x00', \
        'ServerSendMessageToPlayers not as expected (already patched or game updated)'
    old_len = b.find(tail) + 2 - head
    old_refs = (old_mem - old_len) // 4
    # Staged is the local 0x114f5; MessageObject = 0x10dc4
    call = E(b'\x1c', H, ctxm(0x114f5, 0x10dc4), b'\x16')
    filler = b'\x0f\x2b' + struct.pack('<i', 0x114f4) + b'\x25'   # TimeStamp = 0: harmless, it is assigned again later; only adds a reference
    extra = old_refs - call[1]
    assert 0 <= extra and len(call[0]) + extra * len(filler) <= old_len
    new = call[0] + filler * extra
    b[head:head + old_len] = new + b'\x0b' * (old_len - len(new))
    yield off, bytes(b)

    off, size = pkg.export('GFxData_Products_TA.UpdateProductData')
    b = bytearray(pkg.img[off:off + size])
    code_len = i32(b, 0x2c)
    assert b[0x30:0x32] == b'\x0f\x2b' and b[0x30 + code_len - 3:0x30 + code_len] == b'\x04\x0b\x4c', \
        'UpdateProductData not as expected (already patched or game updated)'
    payload = ctxm(P, -4731)
    text = E(b'\x5e\x35', Ref(-4459), Ref(-4300), b'\x00\x00', payload)   # MessageObject.Payload.MessageText
    cut = lambda n: b'\x38\x3a\x24' + bytes([n])                      # int(byte n)
    left = lambda n, s: E(b'\xbf\x80', text, cut(n), b'\x16', lit(s), b'\x16')
    mid = lambda n: E(b'\xd0', text, cut(n), cut(255), b'\x16')
    pri = E(b'\x19\x00\x01', Ref(70835), b'\x09\x00', Ref(-3726), b'\x00\x01', Ref(-3726))   # OwnerPC.PlayerReplicationInfo
    san = E(b'\x2b', Ref(SAN))
    set_admin = E(b'\x1c', Ref(57963), b'\x27\x16')                   # PRI_TA.SetMatchAdmin(true)
    is_admin = E(b'\x5e\x19\x00', pri, b'\x09\x00', Ref(57518), b'\x00\x01', Ref(57518))
    name = pkg.names.index('ConsoleCommand')
    # EatString(ReturnValue), virtual call, bWriteToLog = false
    cmd = lambda arg: E(b'\x0e', Ref(-4403), b'\x1b', struct.pack('<ii', name, 0), arg, b'\x28\x16')   # a name is 8 bytes either way
    opts = '?' + url.split('?', 1)[1]
    # Log("Chat <name>: <text>"): runs after the login masked its password, so the log never holds it
    log = E(b'\xe7\xf8\xf8\xf8', lit('Chat '), E(b'\x5e\x19\x00', pri, b'\x09\x00', Ref(-4435), b'\x00\x01', Ref(-4435)),
            b'\x16', lit(': '), b'\x16', text, b'\x16', b'\x48\x48\x16')
    items = [('jn', 'cmds', left(7, '!admin ')),
             ('jn', 'mask', parse_arg('AdminPassword=', san)),
             ('jn', 'grant', E(b'\xc0', mid(7), san, b'\x16')),    # != : the jump is taken when the password matches
             ('j', 'mask'),
             ('lbl', 'grant'),
             ('stmt', E(b'\x5e\x19\x00', pri, struct.pack('<H', mem(set_admin)), Ref(0), b'\x00', set_admin)),
             ('lbl', 'mask'),
             ('stmt', E(b'\x0f\x5e\x35', Ref(-4459), Ref(-4300), b'\x00\x01', payload, lit('!admin ****'))),
             ('j', 'end'),
             ('lbl', 'cmds'),
             ('jn', 'end', is_admin),
             ('jn', 'notmap', left(5, '!map ')),
             ('stmt', cmd(E(b'\xf8\xf8', lit('servertravel '), mid(5), b'\x16', lit(opts), b'\x16'))),
             ('lbl', 'notmap'),
             ('jn', 'end', left(6, '!kick ')),
             ('stmt', E(b'\x1c', Ref(0x114bf), mid(6), b'\x16')),
             ('lbl', 'end'),
             ('stmt', log)]
    out = assemble(items)
    assert len(out[0]) + 3 <= code_len, f'chat hook too long by {len(out[0]) + 3 - code_len} bytes'
    pad = code_len - 1 - len(out[0]) - 2
    struct.pack_into('<i', b, 0x28, mem(out) + 2 + pad + 1)   # memory size; the padding has no references
    b[0x30:0x30 + code_len] = out[0] + b'\x04\x0b' + b'\x0b' * pad + b'\x4c'
    yield off, bytes(b)

    # SendSignedMessage is client-only as well. Its body becomes the kick loop (its closure local `_0x1` is the loop variable):
    #   foreach WorldInfo.AllControllers(class'PlayerController_X', PC)
    #       if (PC.PlayerReplicationInfo.PlayerName ~= Message) PC.KickPlayerForReason("TAGame.Lan.HostExited");
    off, size = pkg.export('TextChatActor_TA.SendSignedMessage')
    b = bytearray(pkg.img[off:off + size])
    code_len = i32(b, 0x2c)
    assert b[0x30 + code_len - 3:0x30 + code_len] == b'\x04\x0b\x4c' and b[0x30:0x32] == b'\x0f\x2b', \
        'SendSignedMessage not as expected (already patched or game updated)'
    pc = Ref(0x114bb)
    head = E(b'\x2f\x5e\x19\x00\x12\x00\x20', Ref(-977), b'\x0a\x00', Ref(-3813), b'\x00\x1c', Ref(-2447), b'\x16')  # WorldInfo.GetWorldInfo()
    allc = E(b'\x1c', Ref(-2433), b'\x20', Ref(-1172), b'\x2b', pc, b'\x16')   # .AllControllers(class'PlayerController_X', PC)
    pri_name = E(b'\x5e\x19\x00\x19\x00\x2b', pc, b'\x09\x00', Ref(-3726), b'\x00\x01', Ref(-3726),
                 b'\x09\x00', Ref(-4435), b'\x00\x01', Ref(-4435))
    cond = E(b'\xbf', pri_name, b'\x2b', Ref(0x114be), b'\x16')
    kcall = E(b'\x1c', Ref(-3221), lit('TAGame.Lan.HostExited'), b'\x48\x16')
    kick = E(b'\x5e\x19\x00\x2b', pc, struct.pack('<H', mem(kcall)), Ref(0), b'\x00', kcall)
    start = mem(head) + 11 + mem(allc) + 2       # memory offset of the loop body
    end = start + 3 + mem(cond) + mem(kick)      # IteratorNext; IteratorPop follows it
    skip = mem(allc) + 2 + (end - start) + 2
    out = E(head, struct.pack('<H', skip), Ref(0), b'\x00', allc, struct.pack('<H', end + 1),
            b'\x07', struct.pack('<H', end), cond, kick, b'\x31\x30\x04\x0b')
    assert len(out[0]) < code_len, f'kick loop too long by {len(out[0]) - code_len + 1} bytes'
    pad = code_len - 1 - len(out[0])
    struct.pack_into('<i', b, 0x28, mem(out) + pad + 1)
    b[0x30:0x30 + code_len] = out[0] + b'\x0b' * pad + b'\x4c'
    yield off, bytes(b)


def password_edits(pkg):
    # Join password. ListenServer_TA.AllowPlayerLogin rejects a joining player unless the `Password` URL option equals
    # GetCustomMatchSettings().Password, when that is not empty. The server has no profile, so the settings came back empty.
    # GetCustomMatchSettings now fills only the password, from the -JoinPassword=<pw> command line option:
    #   ParseCommandlineString("JoinPassword=", ReturnValue.Password);  return ReturnValue;
    off, size = pkg.export('ListenServer_TA.GetCustomMatchSettings')
    b = bytearray(pkg.img[off:off + size])
    code_len = i32(b, 0x2c)
    assert b[0x30:0x32] == b'\x04\x5e' and b[0x30 + code_len - 7:0x30 + code_len - 5] == b'\x04\x3a', \
        'GetCustomMatchSettings not as expected (already patched or game updated)'
    ret = Ref(i32(b, 0x30 + code_len - 5))
    out = E(parse_arg('JoinPassword=', E(b'\x5e\x35', Ref(-4452), Ref(-4296), b'\x00\x01\x2b', ret)), b'\x04\x3a', ret)
    pad = code_len - 1 - len(out[0])
    assert pad >= 0, 'GetCustomMatchSettings replacement too long'
    struct.pack_into('<i', b, 0x28, mem(out) + pad + 1)
    b[0x30:0x30 + code_len] = out[0] + b'\x0b' * pad + b'\x4c'
    yield off, bytes(b)


def patch(src, dst, edits, url):
    pkg = Package(open(src, 'rb').read())
    done = list(edits(pkg, url))
    for off, data in done:
        pkg.write(off, data)
    out = pkg.repack()
    check = Package(out)  # self-check: the written file decodes back to exactly the patched bytes
    for off, data in done:
        assert check.img[off:off + len(data)] == data, 'round trip failed'
    open(dst, 'wb').write(out)
    print(f'patched {len(done)} exports -> {dst}')


def main():
    src, dst = sys.argv[1], sys.argv[2]
    url = URL.format(sys.argv[3] if len(sys.argv) > 3 else 'Stadium_P')
    patch(f'{src}/ProjectX.upk', f'{dst}/ProjectX.upk', projectx_edits, url)
    patch(f'{src}/TAGame.upk', f'{dst}/TAGame.upk', tagame_edits, url)
    print(f'travel URL: {url}')


if __name__ == '__main__':
    main()
