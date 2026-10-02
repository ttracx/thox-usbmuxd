# SPDX-License-Identifier: GPL-3.0-or-later
"""Operator CLI. No keys or document contents are written to logs."""
from __future__ import annotations

import argparse
import asyncio
import base64
import binascii
import ipaddress
import logging
import math
import os
from pathlib import Path
import stat
import sys

from .jobs import JobService
from .protocol import ProtocolError, client_handshake

LOG = logging.getLogger("thox_usb")


def create_pair_key(output: Path, reveal: bool = False) -> None:
    output = output.absolute()
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    key = base64.b64encode(os.urandom(32)) + b"\n"
    # Exclusive creation refuses existing files and symlinks, even with --reveal.
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(key)
        stream.flush()
        os.fsync(stream.fileno())
    print(str(output))
    if reveal:
        print(key.decode("ascii").strip())


def read_pair_key(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise ValueError("Pairing key must be a regular file with permissions 600.")
        if hasattr(os, "getuid") and info.st_uid != os.getuid():
            raise ValueError("Pairing key must be owned by the current user.")
        encoded = stream.read(257)
    if len(encoded) > 256:
        raise ValueError("Pairing key file is too large.")
    try:
        key = base64.b64decode(encoded.strip(), validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Pairing key must be base64 encoding of 32 bytes.") from exc
    if len(key) != 32:
        raise ValueError("Pairing key must contain exactly 32 bytes.")
    return key


def loopback_host(value: str) -> str:
    # Pin localhost to a literal address so name resolution cannot change scope.
    value = "127.0.0.1" if value == "localhost" else value
    try:
        if not ipaddress.ip_address(value).is_loopback:
            raise ValueError
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Bridge host must be a literal loopback address.") from exc
    return value


def port_number(value: str) -> int:
    try:
        number = int(value)
        if not 1 <= number <= 65535:
            raise ValueError
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Port must be between 1 and 65535.") from exc
    return number


def reconnect_delay(value: str) -> float:
    try:
        number = float(value)
        if not math.isfinite(number) or not 0.1 <= number <= 60:
            raise ValueError
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Reconnect delay must be between 0.1 and 60 seconds.") from exc
    return number


async def bridge(args: argparse.Namespace) -> None:
    key = read_pair_key(args.pair_key)
    service = JobService(args.workspace, inference_url=args.inference_url, model=args.model)
    await service.start()
    LOG.info("Host service started; analyze is deterministic statistics, not LLM inference.")
    LOG.info("Local inference is %s.", "configured" if args.inference_url else "disabled")
    try:
        while True:
            writer = None
            try:
                reader, writer = await asyncio.wait_for(asyncio.open_connection(args.host, args.port), timeout=10)
                session = await client_handshake(reader, writer, key)
                ready = await asyncio.wait_for(session.receive(), timeout=10)
                if ready != {"type": "ready", "version": 1} or type(ready.get("version")) is not int:
                    raise ProtocolError("Expected authenticated ready message")
                LOG.info("Paired app connected; submitted jobs persist across link loss.")
                while True:
                    message = await session.receive()
                    response = await service.handle(message)
                    await session.send(response)
            except asyncio.CancelledError:
                raise
            except (OSError, EOFError, ConnectionError, asyncio.IncompleteReadError, asyncio.TimeoutError, ProtocolError):
                # Avoid provider errors, document text, raw frame bytes, or keys in logs.
                LOG.warning("Connection unavailable or authentication failed; retrying in %.1fs.", args.reconnect)
            finally:
                if writer is not None:
                    writer.close()
                    try:
                        await writer.wait_closed()
                    except (OSError, ConnectionError):
                        pass
            await asyncio.sleep(args.reconnect)
    finally:
        await service.close()


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="THOX Mini USB POC host (experimental)")
    commands = result.add_subparsers(dest="command", required=True)
    pair = commands.add_parser("pair", help="Create an owner-only pairing key without overwriting")
    pair.add_argument("--output", required=True, type=Path)
    pair.add_argument("--reveal", action="store_true", help="Explicitly print the secret for entry into the iOS app")
    host = commands.add_parser("bridge", help="Connect to a foreground iOS listener through loopback iproxy")
    host.add_argument("--pair-key", required=True, type=Path)
    host.add_argument("--workspace", required=True, type=Path, help="Dedicated private directory (mode 700)")
    host.add_argument("--host", type=loopback_host, default="127.0.0.1")
    host.add_argument("--port", type=port_number, default=49322, help="Host-side iproxy port (default: 49322)")
    host.add_argument("--reconnect", type=reconnect_delay, default=2.0)
    host.add_argument("--inference-url", help="Optional literal-loopback HTTP(S) /v1/chat/completions URL")
    host.add_argument("--model", help="Required together with --inference-url")
    return result


def main() -> int:
    # Child DB journals and artifacts inherit private defaults.
    os.umask(0o077)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parser().parse_args()
    try:
        if args.command == "pair":
            create_pair_key(args.output, args.reveal)
        else:
            asyncio.run(bridge(args))
    except KeyboardInterrupt:
        return 130
    except (ValueError, OSError) as exc:
        # ValueErrors are our operator configuration messages; filesystem errors
        # are normalized to avoid echoing unexpected paths or external content.
        message = str(exc) if isinstance(exc, ValueError) else "Could not access a required private file or directory."
        LOG.error("%s", message)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
