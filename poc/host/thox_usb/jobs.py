# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded, durable Mini jobs. Analyze mode is statistics, never model inference."""
from __future__ import annotations

import asyncio
import hashlib
import fcntl
import ipaddress
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import stat
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
import uuid

MAX_TEXT_BYTES = 65_536
MAX_PROVIDER_BYTES = 262_144
MAX_RESULT_JSON_BYTES = 131_072  # Leaves room for encrypted/base64 wire framing.
MAX_QUEUED_JOBS = 16
INFERENCE_DEADLINE_SECONDS = 30.0
TERMINAL_STATES = frozenset({"completed", "failed", "cancelled"})


class RequestError(Exception):
    """Safe error content that may be returned to the paired client."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class NoRedirect(HTTPRedirectHandler):
    """A loopback inference endpoint cannot redirect a document off device."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RequestError("provider_redirect", "Inference redirects are disabled.")


def canonical_uuid(value: Any) -> str:
    if not isinstance(value, str):
        raise RequestError("invalid_request", "A canonical UUID string is required.")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise RequestError("invalid_request", "A canonical UUID string is required.") from exc
    if str(parsed) != value:
        raise RequestError("invalid_request", "A canonical lowercase UUID is required.")
    return value


def private_directory(path: Path) -> None:
    """Require a dedicated owner-only directory; never silently loosen access."""
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or path.is_symlink():
        raise ValueError("Workspace and artifact locations must be real directories.")
    if info.st_mode & 0o077:
        raise ValueError("Workspace must be private: chmod 700 the dedicated directory.")
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise ValueError("Workspace must be owned by the current user.")


def validate_inference_url(value: str) -> str:
    """Accept literal loopback only, without DNS, proxies, or redirects."""
    try:
        parsed = urlsplit(value)
        address = ipaddress.ip_address(parsed.hostname or "")
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Inference URL must use a literal loopback IP address.") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not address.is_loopback
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path != "/v1/chat/completions"
        or (port is not None and not 1 <= port <= 65535)
    ):
        raise ValueError("Inference URL must be loopback HTTP(S) /v1/chat/completions.")
    return value


def analyze_text(text: str) -> dict[str, Any]:
    data = text.encode("utf-8")
    return {
        "engine": "deterministic_statistics",
        "is_llm_output": False,
        "execution_location": "mini_host",
        "characters": len(text),
        "utf8_bytes": len(data),
        "words": len(text.split()),
        "lines": len(text.splitlines()),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def inference_request(url: str, model: str, text: str) -> dict[str, Any]:
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": text}],
                       "stream": False, "max_tokens": 256}).encode("utf-8")
    request = Request(url, data=body, method="POST",
                      headers={"Content-Type": "application/json", "Accept": "application/json"})
    opener = build_opener(ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request, timeout=30) as response:
            data = response.read(MAX_PROVIDER_BYTES + 1)
        if len(data) > MAX_PROVIDER_BYTES:
            raise RequestError("provider_response_too_large", "Local inference response exceeded its size limit.")
        payload = json.loads(data)
        content = payload["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("Expected text content")
        content.encode("utf-8")
    except RequestError:
        raise
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RequestError("provider_unavailable", "Local inference failed or timed out.") from exc
    except (ValueError, KeyError, IndexError, TypeError, UnicodeError) as exc:
        raise RequestError("provider_invalid_response", "Local inference returned an invalid response.") from exc
    result = {"engine": "openai_compatible_local_endpoint", "is_llm_output": True,
              "execution_location": "mini_host", "model": model, "text": content}
    if len(json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) > MAX_RESULT_JSON_BYTES:
        raise RequestError("provider_response_too_large", "Local inference output exceeds the encrypted response limit.")
    return result


def inference_process(connection, url: str, model: str, text: str) -> None:
    """A killable child bounds provider wall time, including slow-drip responses."""
    try:
        result = {"ok": True, "result": inference_request(url, model, text)}
    except RequestError as exc:
        result = {"ok": False, "error": {"code": exc.code, "message": exc.message}}
    except Exception:
        result = {"ok": False, "error": {"code": "provider_failed", "message": "Local inference process failed."}}
    try:
        connection.send_bytes(json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    finally:
        connection.close()


class JobService:
    """One worker with a 16-item pending queue and private SQLite persistence.

    Connection loss does not stop this service. Restarting it marks any unfinished
    job failed rather than resubmitting inference or other work automatically.
    """

    def __init__(self, workspace: Path | str, inference_url: str | None = None,
                 model: str | None = None) -> None:
        if bool(inference_url) != bool(model):
            raise ValueError("Configure both inference URL and model, or neither.")
        if model is not None and (len(model) > 256 or any(ord(c) < 32 for c in model)):
            raise ValueError("Model must be a nonempty identifier of at most 256 characters.")
        self.inference_url = validate_inference_url(inference_url) if inference_url else None
        self.model = model
        self.workspace = Path(workspace).absolute()
        private_directory(self.workspace)
        self.artifacts = self.workspace / "artifacts"
        private_directory(self.artifacts)
        self.db_path = self.workspace / "jobs.sqlite3"
        try:
            fd = os.open(self.db_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            info = self.db_path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
                raise ValueError("Job database must be a private regular file.")
            if hasattr(os, "getuid") and info.st_uid != os.getuid():
                raise ValueError("Job database must be owned by the current user.")
        else:
            os.close(fd)
        self.db = sqlite3.connect(self.db_path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=DELETE")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, status TEXT NOT NULL, mode TEXT NOT NULL,
            text TEXT NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL,
            result TEXT, error TEXT
        )""")
        self.db.commit()
        self._lock_fd = os.open(self.workspace / ".host.lock", os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            lock_info = os.fstat(self._lock_fd)
            if not stat.S_ISREG(lock_info.st_mode) or lock_info.st_mode & 0o077:
                raise ValueError("Workspace lock must be a private regular file.")
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, ValueError) as exc:
            os.close(self._lock_fd)
            self.db.close()
            raise ValueError("Workspace is already in use or its private lock is invalid.") from exc
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=MAX_QUEUED_JOBS)
        self.worker: asyncio.Task | None = None
        self._closed = False
        self._active_inference: asyncio.Task | None = None
        self._active_job: str | None = None

    async def start(self) -> None:
        if self._closed:
            raise RuntimeError("Job service is closed.")
        if self.worker is not None:
            return
        error = json.dumps({"code": "interrupted", "message": "Host restarted before job completion; submit a new job explicitly."})
        with self.db:
            self.db.execute("UPDATE jobs SET status='failed', error=?, updated_at=? WHERE status IN ('queued','running')", (error, time.time()))
        self.worker = asyncio.create_task(self._work(), name="thox-job-worker")

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self.worker:
            self.worker.cancel()
            try:
                await self.worker
            except asyncio.CancelledError:
                pass
        # Preserve unfinished status: start() reports interruption on next run.
        self.db.close()
        os.close(self._lock_fd)

    def _get(self, job_id: str) -> dict[str, Any]:
        row = self.db.execute("SELECT id,status,mode,created_at,updated_at,result,error FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise RequestError("not_found", "Job was not found in this workspace.")
        result = dict(row)
        result["result"] = json.loads(row["result"]) if row["result"] else None
        result["error"] = json.loads(row["error"]) if row["error"] else None
        return result

    async def handle(self, request: Any) -> dict[str, Any]:
        """Validate a single message and return an intentionally small response."""
        request_id = None
        try:
            if not isinstance(request, dict):
                raise RequestError("invalid_request", "Request must be an object.")
            request_id = canonical_uuid(request.get("id"))
            if set(request) != {"type", "id", "op", "args"} or request["type"] != "request":
                raise RequestError("invalid_request", "Expected type, id, op, and args only.")
            if not isinstance(request["op"], str) or not isinstance(request["args"], dict):
                raise RequestError("invalid_request", "Operation must be a string and args an object.")
            if self._closed or self.worker is None or self.worker.done():
                raise RequestError("unavailable", "Job service is not running.")
            result = self._dispatch(request["op"], request["args"], request_id)
            return {"type": "response", "id": request_id, "ok": True, "result": result}
        except RequestError as exc:
            return {"type": "response", "id": request_id, "ok": False,
                    "error": {"code": exc.code, "message": exc.message}}
        except (OSError, sqlite3.Error, UnicodeError):
            return {"type": "response", "id": request_id, "ok": False,
                    "error": {"code": "storage_error", "message": "The host could not persist this operation."}}

    def _dispatch(self, op: str, args: dict[str, Any], request_id: str) -> dict[str, Any]:
        if op in {"ping", "status"}:
            if args:
                raise RequestError("invalid_request", "This operation takes no arguments.")
            if op == "ping":
                return {"pong": True}
            return {
                "device": "THOX Mini host POC", "version": "0.1.0",
                "transport": "authenticated_host_initiated_tcp",
                "capabilities": ["analyze", "durable_jobs", "cancel", "artifacts"] + (["inference"] if self.inference_url else []),
                "executor": "mini_host", "analyze_is_llm": False,
                "inference_configured": self.inference_url is not None,
            }
        if op == "job_submit":
            if set(args) != {"text", "mode"} or not isinstance(args.get("text"), str):
                raise RequestError("invalid_request", "Submit requires text and mode only.")
            text, mode = args["text"], args["mode"]
            if not isinstance(mode, str) or mode not in {"analyze", "inference"}:
                raise RequestError("invalid_request", "Mode must be analyze or inference.")
            try:
                encoded = text.encode("utf-8")
            except UnicodeError as exc:
                raise RequestError("invalid_request", "Text must be valid UTF-8.") from exc
            if len(encoded) > MAX_TEXT_BYTES:
                raise RequestError("text_too_large", "Text exceeds the 65536-byte UTF-8 limit.")
            existing = self.db.execute("SELECT mode,text FROM jobs WHERE id=?", (request_id,)).fetchone()
            if existing is not None:
                if existing["mode"] != mode or existing["text"] != text:
                    raise RequestError("conflict", "Submission UUID is already associated with different job content.")
                return self._get(request_id)
            if mode == "inference" and self.inference_url is None:
                raise RequestError("inference_disabled", "The host operator has not configured local inference.")
            if self.queue.full():
                raise RequestError("queue_full", "The 16-job pending queue is full.")
            job_id, now = request_id, time.time()
            with self.db:
                self.db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,NULL,NULL)", (job_id, "queued", mode, text, now, now))
            self.queue.put_nowait(job_id)
            return self._get(job_id)
        if op in {"job_get", "job_cancel"}:
            if set(args) != {"job_id"}:
                raise RequestError("invalid_request", "This operation requires job_id only.")
            job_id = canonical_uuid(args["job_id"])
            job = self._get(job_id)
            if op == "job_cancel" and job["status"] not in TERMINAL_STATES:
                with self.db:
                    self.db.execute("UPDATE jobs SET status='cancelled',updated_at=? WHERE id=?", (time.time(), job_id))
                if self._active_job == job_id and self._active_inference:
                    self._active_inference.cancel()
            return self._get(job_id)
        raise RequestError("unsupported_operation", "Operation is not supported.")

    def _infer(self, text: str) -> dict[str, Any]:
        """Synchronous provider implementation; production jobs use a child process."""
        return inference_request(self.inference_url, self.model, text)

    async def _run_inference(self, text: str) -> dict[str, Any]:
        context = multiprocessing.get_context("spawn")
        receiver, sender = context.Pipe(duplex=False)
        process = context.Process(target=inference_process, args=(sender, self.inference_url, self.model, text), daemon=True)
        try:
            process.start()
            sender.close()
            deadline = time.monotonic() + INFERENCE_DEADLINE_SECONDS
            while True:
                if receiver.poll():
                    try:
                        payload = json.loads(receiver.recv_bytes(MAX_RESULT_JSON_BYTES + 4096))
                    except (OSError, EOFError, ValueError) as exc:
                        raise RequestError("provider_failed", "Local inference process returned an invalid result.") from exc
                    if payload.get("ok") is True:
                        return payload["result"]
                    raise RequestError(payload["error"]["code"], payload["error"]["message"])
                if not process.is_alive():
                    raise RequestError("provider_failed", "Local inference process exited without a result.")
                if time.monotonic() >= deadline:
                    raise RequestError("provider_timeout", "Local inference exceeded the 30-second deadline.")
                await asyncio.sleep(0.05)
        finally:
            sender.close()
            receiver.close()
            if process.pid is not None:
                if process.is_alive():
                    process.terminate()
                # Only the owned child is signaled. Reap it before accepting another job.
                process.join(timeout=1)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=1)
                process.close()

    def _persist_artifact(self, job_id: str, result: dict[str, Any]) -> None:
        path = self.artifacts / (job_id + ".json")
        # IDs originate in uuid4, and the owner-only directory rejects symlinks.
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as output:
                json.dump(result, output, ensure_ascii=False, indent=2)
                output.write("\n")
                output.flush()
                os.fsync(output.fileno())
        except BaseException:
            path.unlink(missing_ok=True)
            raise

    async def _work(self) -> None:
        while True:
            job_id = await self.queue.get()
            try:
                row = self.db.execute("SELECT status,mode,text FROM jobs WHERE id=?", (job_id,)).fetchone()
                if row["status"] != "queued":
                    continue
                with self.db:
                    self.db.execute("UPDATE jobs SET status='running',updated_at=? WHERE id=?", (time.time(), job_id))
                try:
                    if row["mode"] == "analyze":
                        result = analyze_text(row["text"])
                    else:
                        self._active_job = job_id
                        self._active_inference = asyncio.create_task(self._run_inference(row["text"]))
                        try:
                            result = await self._active_inference
                        except asyncio.CancelledError:
                            if self._closed:
                                raise
                            if self._get(job_id)["status"] == "cancelled":
                                continue
                            raise
                        finally:
                            self._active_inference = None
                            self._active_job = None
                    # A cancellation received while inference ran wins over its late result.
                    if self._get(job_id)["status"] != "running":
                        continue
                    self._persist_artifact(job_id, result)
                    with self.db:
                        self.db.execute("UPDATE jobs SET status='completed',result=?,updated_at=? WHERE id=? AND status='running'",
                                        (json.dumps(result, ensure_ascii=False), time.time(), job_id))
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    error = ({"code": exc.code, "message": exc.message} if isinstance(exc, RequestError)
                             else {"code": "execution_failed", "message": "Host could not complete or persist this job."})
                    with self.db:
                        self.db.execute("UPDATE jobs SET status='failed',error=?,updated_at=? WHERE id=? AND status='running'",
                                        (json.dumps(error), time.time(), job_id))
            finally:
                self.queue.task_done()
