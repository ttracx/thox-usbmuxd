# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded, authenticated POC transport. See ../../PROTOCOL.md.

The Mini is the transport client, even though it serves application requests.
This experimental protocol needs independent review before production use.
"""
from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import hmac
import json
import secrets
import struct
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

MAX_FRAME = 1048576
HANDSHAKE_TIMEOUT = 10.0
PREFIX = b"THOX-USB-POC-v1/"


class ProtocolError(Exception):
    """Peer sent invalid or unauthenticated data; close the stream."""


def _object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError("duplicate JSON key")
        result[key] = value
    return result


def _nonfinite(_: str) -> None:
    raise ProtocolError("non-finite JSON number")


def decode_json(data: bytes) -> dict:
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_object,
                           parse_constant=_nonfinite)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ProtocolError("invalid JSON") from exc
    if not isinstance(value, dict):
        raise ProtocolError("JSON frame must be an object")
    return value


def encode_json(value: dict) -> bytes:
    if not isinstance(value, dict):
        raise ProtocolError("JSON frame must be an object")
    try:
        encoded = json.dumps(value, separators=(",", ":"), ensure_ascii=False,
                             allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise ProtocolError("invalid outbound JSON") from exc
    if not 0 < len(encoded) <= MAX_FRAME:
        raise ProtocolError("frame too large")
    return encoded


async def read_frame(reader: asyncio.StreamReader) -> dict:
    header = await reader.readexactly(4)
    length = struct.unpack("!I", header)[0]
    if not 0 < length <= MAX_FRAME:
        raise ProtocolError("invalid frame length")
    return decode_json(await reader.readexactly(length))


async def write_frame(writer: asyncio.StreamWriter, value: dict) -> None:
    body = encode_json(value)
    writer.write(struct.pack("!I", len(body)) + body)
    await writer.drain()


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def unb64(value: Any, size: int | None = None) -> bytes:
    if not isinstance(value, str):
        raise ProtocolError("base64 string required")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ProtocolError("invalid base64") from exc
    if size is not None and len(raw) != size:
        raise ProtocolError("incorrect decoded length")
    return raw


def proof(key: bytes, role: str, client_nonce: bytes, server_nonce: bytes) -> bytes:
    return hmac.digest(key, role.encode("ascii") + b"\0" + client_nonce + server_nonce,
                       hashlib.sha256)


def derive_keys(key: bytes, client_nonce: bytes, server_nonce: bytes) -> tuple[bytes, bytes]:
    if len(key) != 32 or len(client_nonce) != 32 or len(server_nonce) != 32:
        raise ProtocolError("32-byte key and nonces required")
    return tuple(HKDF(algorithm=hashes.SHA256(), length=32,
                      salt=client_nonce + server_nonce, info=PREFIX + direction).derive(key)
                 for direction in (b"client", b"server"))


class SecureSession:
    """One reader and serialized writers; sequence counters reject replay/order errors."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                 client_key: bytes, server_key: bytes, *, is_client: bool):
        self.reader, self.writer = reader, writer
        self.tx_direction = b"client" if is_client else b"server"
        self.rx_direction = b"server" if is_client else b"client"
        self.tx = AESGCM(client_key if is_client else server_key)
        self.rx = AESGCM(server_key if is_client else client_key)
        self.tx_sequence = self.rx_sequence = 0
        self._send_lock = asyncio.Lock()

    @staticmethod
    def _parameters(direction: bytes, sequence: int) -> tuple[bytes, bytes]:
        if not 0 <= sequence < 2**64:
            raise ProtocolError("sequence exhausted")
        counter = struct.pack("!Q", sequence)
        return b"\0" * 4 + counter, PREFIX + direction + b"\0" + counter

    async def send(self, message: dict) -> None:
        async with self._send_lock:
            nonce, aad = self._parameters(self.tx_direction, self.tx_sequence)
            ciphertext = self.tx.encrypt(nonce, encode_json(message), aad)
            await write_frame(self.writer, {"seq": self.tx_sequence, "data": b64(ciphertext)})
            self.tx_sequence += 1

    async def receive(self) -> dict:
        envelope = await read_frame(self.reader)
        sequence = envelope.get("seq")
        if set(envelope) != {"seq", "data"} or type(sequence) is not int or sequence != self.rx_sequence:
            raise ProtocolError("unexpected sequence or envelope")
        nonce, aad = self._parameters(self.rx_direction, sequence)
        try:
            plaintext = self.rx.decrypt(nonce, unb64(envelope["data"]), aad)
        except (InvalidTag, ValueError) as exc:
            raise ProtocolError("authentication failed") from exc
        result = decode_json(plaintext)
        self.rx_sequence += 1
        return result

    async def close(self) -> None:
        self.writer.close()
        try:
            await self.writer.wait_closed()
        except (OSError, ConnectionError):
            pass


async def client_handshake(reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                           key: bytes) -> SecureSession:
    async def handshake() -> SecureSession:
        if len(key) != 32:
            raise ProtocolError("32-byte pairing key required")
        cn = secrets.token_bytes(32)
        await write_frame(writer, {"type": "hello", "version": 1, "nonce": b64(cn)})
        ack = await read_frame(reader)
        if set(ack) != {"type", "version", "nonce", "proof"} or ack["type"] != "hello_ack" or type(ack["version"]) is not int or ack["version"] != 1:
            raise ProtocolError("invalid hello acknowledgement")
        sn = unb64(ack["nonce"], 32)
        if not hmac.compare_digest(unb64(ack["proof"], 32), proof(key, "server", cn, sn)):
            raise ProtocolError("pairing authentication failed")
        await write_frame(writer, {"type": "auth", "proof": b64(proof(key, "client", cn, sn))})
        return SecureSession(reader, writer, *derive_keys(key, cn, sn), is_client=True)
    return await asyncio.wait_for(handshake(), HANDSHAKE_TIMEOUT)


async def server_handshake(reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                           key: bytes) -> SecureSession:
    """Test peer reference implementation; production iOS uses CryptoKit."""
    async def handshake() -> SecureSession:
        if len(key) != 32:
            raise ProtocolError("32-byte pairing key required")
        hello = await read_frame(reader)
        if set(hello) != {"type", "version", "nonce"} or hello["type"] != "hello" or type(hello["version"]) is not int or hello["version"] != 1:
            raise ProtocolError("invalid hello")
        cn, sn = unb64(hello["nonce"], 32), secrets.token_bytes(32)
        await write_frame(writer, {"type": "hello_ack", "version": 1, "nonce": b64(sn),
                                   "proof": b64(proof(key, "server", cn, sn))})
        auth = await read_frame(reader)
        if set(auth) != {"type", "proof"} or auth["type"] != "auth" or not hmac.compare_digest(unb64(auth["proof"], 32), proof(key, "client", cn, sn)):
            raise ProtocolError("pairing authentication failed")
        session = SecureSession(reader, writer, *derive_keys(key, cn, sn), is_client=False)
        await session.send({"type": "ready", "version": 1})
        return session
    return await asyncio.wait_for(handshake(), HANDSHAKE_TIMEOUT)
