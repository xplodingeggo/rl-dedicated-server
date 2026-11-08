"""Answer Rocket League's LAN browser for the dedicated server.

The game's LAN browser broadcasts a LanMessage_HostQuery_X to UDP 14001 and lists every
LanMessage_HostResponse_X that echoes its nonce. A dedicated server never starts its own responder
(UdpLanServer_X), so this script answers instead; picking the match runs `open <ServerID>?Lan?...`.

usage: python lan_responder.py [map] [server name] [-v]
"""
import json
import re
import socket
import struct
import sys

PORT = 14001
GAME_PORT = 7777
RESPONSE = b'ProjectX.LanMessage_HostResponse_X'
args = [a for a in sys.argv[1:] if a != '-v']
VERBOSE = '-v' in sys.argv
MAP = args[0] if args else 'Stadium_P'
NAME = args[1] if len(args) > 1 else 'Dedicated server'


def local_ip_for(peer):
    # the address of the interface that routes to the peer: what the peer can join
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((peer, PORT))
        return s.getsockname()[0]
    finally:
        s.close()


def parse(packet):
    """-> (message class, JSON body text) for '<u32 BE len><class>\\0<json>' packets"""
    if len(packet) < 5:
        return None, None
    n = struct.unpack_from('>I', packet)[0]
    if not 0 < n < 128 or len(packet) < 4 + n + 1:
        return None, None
    return packet[4:4 + n], packet[4 + n + 1:].decode('utf-8', 'replace')


def response(query, server_id):
    # the nonce and BuildID are copied as raw JSON text so their encoding (Qword, int) round-trips exactly
    nonce = re.search(r'"Nonce"\s*:\s*("[^"]*"|-?\d+)', query)
    build = re.search(r'"BuildID"\s*:\s*(-?\d+)', query)
    if not nonce:
        return None
    meta = json.dumps({'ServerName': NAME, 'ServerMap': MAP, 'bPassword': False, 'NumPlayers': 0,
                       'MaxPlayers': 6, 'BuildID': int(build.group(1)) if build else 0},
                      separators=(',', ':'))  # the game's JSON has no spaces
    body = '{"Nonce":%s,"Result":{"Address":""},"ServerID":%s,"MetaData":%s}' % (
        nonce.group(1), json.dumps(server_id), json.dumps(meta))
    return struct.pack('>I', len(RESPONSE)) + RESPONSE + b'\0' + body.encode()


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # the game's own browser shares 14001
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.bind(('0.0.0.0', PORT))
    print(f'answering LAN searches on :{PORT} for {MAP} ("{NAME}")', flush=True)
    while True:
        packet, (host, _) = s.recvfrom(65535)
        cls, body = parse(packet)
        if VERBOSE:
            print(f'<- {host}: {packet[:400]!r}', flush=True)
        if cls != b'ProjectX.LanMessage_HostQuery_X':
            continue
        reply = response(body, f'{local_ip_for(host)}:{GAME_PORT}')
        if reply is None:
            print(f'query from {host} without a nonce: {body[:200]}', flush=True)
            continue
        # the browser listens on the shared broadcast port, like a hosting game's reply
        for dst in ('255.255.255.255', host):
            s.sendto(reply, (dst, PORT))
        print(f'answered {host}', flush=True)


if __name__ == '__main__':
    main()
