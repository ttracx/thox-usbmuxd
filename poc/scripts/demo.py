#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Hardware-free application demo. Uses the real bridge and an iOS protocol mock."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "host"))
from thox_usb.__main__ import bridge, create_pair_key, read_pair_key
from thox_usb.protocol import server_handshake


async def main():
    os.umask(0o077)
    peers = asyncio.Queue()
    with tempfile.TemporaryDirectory(prefix="thox-usb-demo-") as temporary:
        root = Path(temporary)
        key_path = root / "pair.key"
        create_pair_key(key_path)
        key = read_pair_key(key_path)

        async def peer_connected(reader, writer):
            try:
                await peers.put(await server_handshake(reader, writer, key))
            except Exception:
                writer.close()

        listener = await asyncio.start_server(peer_connected, "127.0.0.1", 0)
        args = argparse.Namespace(pair_key=key_path, workspace=root / "workspace",
            host="127.0.0.1", port=listener.sockets[0].getsockname()[1], reconnect=0.1,
            inference_url=None, model=None)
        worker = asyncio.create_task(bridge(args))

        async def request(peer, op, args):
            ident = str(uuid.uuid4())
            await peer.send({"type": "request", "id": ident, "op": op, "args": args})
            response = await asyncio.wait_for(peer.receive(), 5)
            if not response.get("ok"):
                raise RuntimeError(response.get("error"))
            return response["result"]

        current = None
        try:
            async with listener:
                current = await asyncio.wait_for(peers.get(), 5)
                print(json.dumps({"demo": "encrypted loopback; iOS peer simulated",
                                  "status": await request(current, "status", {})}))
                job = await request(current, "job_submit", {"text": "Your AI. Your Data. Your Rules.™", "mode": "analyze"})
                await current.close()
                current = await asyncio.wait_for(peers.get(), 5)
                for _ in range(50):
                    result = await request(current, "job_get", {"job_id": job["id"]})
                    if result["status"] in {"completed", "failed", "cancelled"}:
                        break
                    await asyncio.sleep(0.02)
                if result["status"] != "completed":
                    raise RuntimeError("Demo job did not complete")
                print(json.dumps({"reconnected": True, "job": result}, indent=2))
                # Close accepted streams before Server.__aexit__ waits for them.
                await current.close()
                current = None
                worker.cancel()
                await asyncio.gather(worker, return_exceptions=True)
        finally:
            if current:
                await current.close()
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
