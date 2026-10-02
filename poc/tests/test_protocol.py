# SPDX-License-Identifier: GPL-3.0-or-later
import asyncio
import json
import struct
import unittest
from unittest.mock import patch

from thox_usb.protocol import (MAX_FRAME, ProtocolError, SecureSession, b64,
                               client_handshake, server_handshake, derive_keys,
                               decode_json, read_frame, write_frame)


class MemoryWriter:
    def __init__(self):
        self.data = bytearray()

    def write(self, data):
        self.data.extend(data)

    async def drain(self):
        pass


def reader_for(data):
    reader = asyncio.StreamReader()
    reader.feed_data(data)
    reader.feed_eof()
    return reader


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_split_and_coalesced_frames(self):
        writer = MemoryWriter()
        await write_frame(writer, {"text": "hello 🌍"})
        await write_frame(writer, {"next": True})
        reader = asyncio.StreamReader()
        task = asyncio.create_task(read_frame(reader))
        for byte in writer.data:
            reader.feed_data(bytes([byte]))
            await asyncio.sleep(0)
        self.assertEqual(await task, {"text": "hello 🌍"})
        self.assertEqual(await read_frame(reader), {"next": True})

    async def test_reject_lengths_without_reading_body(self):
        for size in (0, MAX_FRAME + 1, 2**32 - 1):
            with self.subTest(size=size), self.assertRaises(ProtocolError):
                await read_frame(reader_for(struct.pack("!I", size)))

    async def test_truncated_frame(self):
        with self.assertRaises(asyncio.IncompleteReadError):
            await read_frame(reader_for(struct.pack("!I", 10) + b"{}"))

    def test_reject_duplicate_nested_key_and_invalid_json(self):
        for data in (b'{"a":1,"a":2}', b'{"nested":{"x":1,"x":2}}',
                     b'{"a":NaN}', b'[]', b'\xff', b'{'):
            with self.subTest(data=data), self.assertRaises(ProtocolError):
                decode_json(data)

    async def encrypted(self):
        keys = derive_keys(bytes(range(32)), bytes(range(32, 64)), bytes(range(64, 96)))
        writer = MemoryWriter()
        sender = SecureSession(None, writer, *keys, is_client=True)
        await sender.send({"secret": "never plaintext"})
        return keys, writer

    async def test_encrypt_decrypt(self):
        keys, writer = await self.encrypted()
        self.assertNotIn(b"never plaintext", writer.data)
        receiver = SecureSession(reader_for(writer.data), None, *keys, is_client=False)
        self.assertEqual(await receiver.receive(), {"secret": "never plaintext"})

    async def test_maximum_text_with_json_escaping_fits(self):
        keys = derive_keys(bytes(32), bytes(32), bytes([1]) * 32)
        writer = MemoryWriter()
        sender = SecureSession(None, writer, *keys, is_client=False)
        payload = {"type": "request", "id": "00000000-0000-0000-0000-000000000000",
                   "op": "job_submit", "args": {"text": "\0" * 65536, "mode": "analyze"}}
        await sender.send(payload)
        receiver = SecureSession(reader_for(writer.data), None, *keys, is_client=True)
        self.assertEqual(await receiver.receive(), payload)

    async def test_replay_rejected(self):
        keys, writer = await self.encrypted()
        receiver = SecureSession(reader_for(writer.data * 2), None, *keys, is_client=False)
        await receiver.receive()
        with self.assertRaises(ProtocolError):
            await receiver.receive()

    async def test_ciphertext_tampering_rejected(self):
        keys, writer = await self.encrypted()
        envelope = json.loads(writer.data[4:])
        envelope["data"] = b64(b"\0" * 32)
        tampered = MemoryWriter()
        await write_frame(tampered, envelope)
        receiver = SecureSession(reader_for(tampered.data), None, *keys, is_client=False)
        with self.assertRaises(ProtocolError):
            await receiver.receive()
        self.assertEqual(receiver.rx_sequence, 0)

    async def test_boolean_sequence_rejected(self):
        keys, writer = await self.encrypted()
        envelope = json.loads(writer.data[4:])
        envelope["seq"] = False
        tampered = MemoryWriter()
        await write_frame(tampered, envelope)
        with self.assertRaises(ProtocolError):
            await SecureSession(reader_for(tampered.data), None, *keys, is_client=False).receive()

    async def test_wrong_direction_rejected(self):
        keys, writer = await self.encrypted()
        with self.assertRaises(ProtocolError):
            await SecureSession(reader_for(writer.data), None, *keys, is_client=True).receive()

    async def test_nonce_pair_changes_keys(self):
        key = bytes(32)
        self.assertNotEqual(derive_keys(key, bytes(32), bytes(32)),
                            derive_keys(key, bytes(32), bytes([1]) * 32))

    async def test_handshake_and_bidirectional_requests(self):
        key = bytes(range(32))
        finished = asyncio.get_running_loop().create_future()

        async def serve(reader, writer):
            try:
                server = await server_handshake(reader, writer, key)
                await server.send({"type": "request", "op": "ping"})
                self.assertEqual(await server.receive(), {"pong": True})
                finished.set_result(True)
            except Exception as exc:
                finished.set_exception(exc)
            finally:
                writer.close()
                await writer.wait_closed()

        listener = await asyncio.start_server(serve, "127.0.0.1", 0)
        async with listener:
            reader, writer = await asyncio.open_connection("127.0.0.1", listener.sockets[0].getsockname()[1])
            client = await client_handshake(reader, writer, key)
            self.assertEqual(await client.receive(), {"type": "ready", "version": 1})
            self.assertEqual((await client.receive())["op"], "ping")
            await client.send({"pong": True})
            await asyncio.wait_for(finished, 3)
            await client.close()

    async def test_wrong_pair_key_cannot_connect(self):
        done = asyncio.get_running_loop().create_future()

        async def serve(reader, writer):
            try:
                await server_handshake(reader, writer, bytes(32))
            except (ProtocolError, asyncio.IncompleteReadError):
                pass
            finally:
                writer.close()
                await writer.wait_closed()
                done.set_result(True)

        listener = await asyncio.start_server(serve, "127.0.0.1", 0)
        async with listener:
            reader, writer = await asyncio.open_connection("127.0.0.1", listener.sockets[0].getsockname()[1])
            with self.assertRaises(ProtocolError):
                await client_handshake(reader, writer, bytes([1]) * 32)
            writer.close()
            await writer.wait_closed()
            await asyncio.wait_for(done, 3)

    async def test_handshake_timeout(self):
        with patch("thox_usb.protocol.HANDSHAKE_TIMEOUT", 0.01):
            with self.assertRaises(asyncio.TimeoutError):
                await client_handshake(asyncio.StreamReader(), MemoryWriter(), bytes(32))


if __name__ == "__main__":
    unittest.main()
