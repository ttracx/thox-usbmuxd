# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise application jobs over a real encrypted loopback stream, then reconnect."""
import asyncio
from pathlib import Path
import tempfile
import unittest
import uuid

from thox_usb.jobs import JobService
from thox_usb.protocol import client_handshake, server_handshake


class WorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_submit_disconnect_reconnect_recover_result(self):
        key = bytes(range(32))
        peers = asyncio.Queue()
        tasks = set()

        async def ios_peer(reader, writer):
            session = await server_handshake(reader, writer, key)
            await peers.put(session)

        async def mini_connect(service, port):
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            client = await client_handshake(reader, writer, key)
            self.assertEqual((await client.receive())["type"], "ready")

            async def respond():
                try:
                    while True:
                        request = await client.receive()
                        await client.send(await service.handle(request))
                except (asyncio.IncompleteReadError, ConnectionError):
                    pass
                finally:
                    await client.close()
            task = asyncio.create_task(respond())
            tasks.add(task)
            return task

        async def request(peer, op, args):
            ident = str(uuid.uuid4())
            await peer.send({"type": "request", "id": ident, "op": op, "args": args})
            response = await asyncio.wait_for(peer.receive(), 3)
            self.assertEqual(response["id"], ident)
            self.assertTrue(response["ok"], response)
            return response["result"]

        with tempfile.TemporaryDirectory() as directory:
            service = JobService(Path(directory) / "private")
            await service.start()
            listener = await asyncio.start_server(ios_peer, "127.0.0.1", 0)
            try:
                async with listener:
                    port = listener.sockets[0].getsockname()[1]
                    first = await mini_connect(service, port)
                    peer = await asyncio.wait_for(peers.get(), 3)
                    status = await request(peer, "status", {})
                    self.assertFalse(status["inference_configured"])
                    job = await request(peer, "job_submit", {"text": "THOX local\nprivate workspace", "mode": "analyze"})
                    await peer.close()
                    await asyncio.wait_for(first, 3)
                    await mini_connect(service, port)
                    resumed = await asyncio.wait_for(peers.get(), 3)
                    for _ in range(30):
                        recovered = await request(resumed, "job_get", {"job_id": job["id"]})
                        if recovered["status"] == "completed":
                            break
                        await asyncio.sleep(0.01)
                    self.assertEqual(recovered["status"], "completed")
                    self.assertEqual(recovered["result"]["words"], 4)
                    self.assertFalse(recovered["result"]["is_llm_output"])
                    await resumed.close()
                    await asyncio.wait_for(asyncio.gather(*tasks), 3)
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                await service.close()
            # Durable result also survives a host process lifecycle restart.
            reopened = JobService(Path(directory) / "private")
            await reopened.start()
            try:
                response = await reopened.handle({"type": "request", "id": str(uuid.uuid4()),
                    "op": "job_get", "args": {"job_id": job["id"]}})
                self.assertEqual(response["result"]["status"], "completed")
            finally:
                await reopened.close()
