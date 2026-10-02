# SPDX-License-Identifier: GPL-3.0-or-later
"""Behavioral tests for persistence, authority bounds, and provider isolation."""
import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import multiprocessing
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import uuid

from thox_usb.jobs import JobService, RequestError, validate_inference_url


def request(op, **args):
    return {"type": "request", "id": str(uuid.uuid4()), "op": op, "args": args}


class JobTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "workspace"
        self.service = JobService(self.path)
        await self.service.start()

    async def asyncTearDown(self):
        await self.service.close()
        self.tmp.cleanup()

    async def test_analyze_persisted_artifact_and_reconnect(self):
        job = (await self.service.handle(request("job_submit", text="hello world\nhi", mode="analyze")))["result"]
        await self.service.queue.join()
        result = (await self.service.handle(request("job_get", job_id=job["id"])))["result"]
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["result"]["words"], 3)
        self.assertEqual(result["result"]["lines"], 2)
        self.assertFalse(result["result"]["is_llm_output"])
        artifact = self.path / "artifacts" / (job["id"] + ".json")
        self.assertEqual(json.loads(artifact.read_text()), result["result"])
        self.assertEqual(artifact.stat().st_mode & 0o777, 0o600)
        await self.service.close()
        self.service = JobService(self.path)
        await self.service.start()
        restored = (await self.service.handle(request("job_get", job_id=job["id"])))["result"]
        self.assertEqual(restored, result)

    async def test_queue_limit_and_restart_never_retries(self):
        ids = []
        for _ in range(16):
            response = await self.service.handle(request("job_submit", text="queued", mode="analyze"))
            self.assertTrue(response["ok"])
            ids.append(response["result"]["id"])
        full = await self.service.handle(request("job_submit", text="rejected", mode="analyze"))
        self.assertEqual(full["error"]["code"], "queue_full")
        await self.service.close()
        self.service = JobService(self.path)
        await self.service.start()
        for job_id in ids:
            job = (await self.service.handle(request("job_get", job_id=job_id)))["result"]
            self.assertEqual(job["status"], "failed")
            self.assertEqual(job["error"]["code"], "interrupted")
        self.assertTrue(self.service.queue.empty())

    async def test_idempotent_submission_and_conflict(self):
        submission = request("job_submit", text="one", mode="analyze")
        first = await self.service.handle(submission)
        replay = await self.service.handle(submission)
        self.assertEqual(first["result"]["id"], submission["id"])
        self.assertEqual(first, replay)
        self.assertEqual(self.service.queue.qsize(), 1)
        conflict = dict(submission, args={"text": "two", "mode": "analyze"})
        self.assertEqual((await self.service.handle(conflict))["error"]["code"], "conflict")
        await self.service.queue.join()
        replay = await self.service.handle(submission)
        self.assertEqual(replay["result"]["status"], "completed")
        self.assertTrue(self.service.queue.empty())

    async def test_input_validation(self):
        samples = [
            {}, [], request("shell", command="ls"), request("ping", extra=True),
            request("job_get", job_id="../../escape"),
            request("job_submit", text="x", mode=[]),
            request("job_submit", text="x", mode="analyze", endpoint="http://evil.example"),
            request("job_submit", text="x", mode="inference"),
            request("job_submit", text="\ud800", mode="analyze"),
            request("job_submit", text="🧠" * 16385, mode="analyze"),
        ]
        for sample in samples:
            self.assertFalse((await self.service.handle(sample))["ok"], repr(sample)[:100])
        boundary = await self.service.handle(request("job_submit", text="🧠" * 16384, mode="analyze"))
        self.assertTrue(boundary["ok"])

    async def test_cancelled_inference_discards_late_result(self):
        await self.service.close()
        self.service = JobService(self.path, "http://127.0.0.1:8080/v1/chat/completions", "test-model")
        started, finish = asyncio.Event(), asyncio.Event()
        async def slow_inference(text):
            started.set()
            try:
                await finish.wait()
            except asyncio.CancelledError:
                # A provider may return after cancellation: the worker still drops it.
                return {"text": "late result"}
            return {"text": "late result"}
        self.service._run_inference = slow_inference
        await self.service.start()
        job = (await self.service.handle(request("job_submit", text="private", mode="inference")))["result"]
        try:
            await asyncio.wait_for(started.wait(), timeout=2)
            cancelled = await self.service.handle(request("job_cancel", job_id=job["id"]))
            self.assertEqual(cancelled["result"]["status"], "cancelled")
        finally:
            finish.set()
        await asyncio.wait_for(self.service.queue.join(), timeout=2)
        result = (await self.service.handle(request("job_get", job_id=job["id"])))["result"]
        self.assertEqual(result["status"], "cancelled")
        self.assertIsNone(result["result"])
        self.assertFalse((self.path / "artifacts" / (job["id"] + ".json")).exists())

    async def test_terminal_cancel_unchanged_and_missing_job(self):
        job = (await self.service.handle(request("job_submit", text="done", mode="analyze")))["result"]
        await self.service.queue.join()
        completed = (await self.service.handle(request("job_get", job_id=job["id"])))["result"]
        after = (await self.service.handle(request("job_cancel", job_id=job["id"])))["result"]
        self.assertEqual(after, completed)
        missing = await self.service.handle(request("job_get", job_id=str(uuid.uuid4())))
        self.assertEqual(missing["error"]["code"], "not_found")

    async def test_workspace_lock_and_permissions(self):
        with self.assertRaises(ValueError):
            JobService(self.path)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.path / "jobs.sqlite3").stat().st_mode & 0o777, 0o600)
        public = self.path.parent / "public"
        public.mkdir(mode=0o755)
        public.chmod(0o755)
        with self.assertRaises(ValueError):
            JobService(public)


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.reply = {"status": 200, "body": json.dumps({"choices": [{"message": {"content": "local response"}}]}).encode()}
        reply = self.reply
        self.received, self.release = threading.Event(), threading.Event()
        self.release.set()
        received, release = self.received, self.release
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                received.set()
                release.wait(timeout=2)
                self.send_response(reply["status"])
                if reply["status"] == 302:
                    self.send_header("Location", "http://example.invalid/off-device")
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(reply["body"])))
                self.end_headers()
                try:
                    self.wfile.write(reply["body"])
                except BrokenPipeError:
                    pass  # Expected when the owned inference client is cancelled.
            def log_message(self, *args):
                pass
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        self.service = JobService(Path(self.tmp.name) / "jobs", f"http://127.0.0.1:{self.server.server_port}/v1/chat/completions", "test")
        await self.service.start()

    async def asyncTearDown(self):
        self.release.set()
        await self.service.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.tmp.cleanup()

    async def test_local_provider_output(self):
        result = self.service._infer("input")
        self.assertEqual(result["text"], "local response")
        self.assertTrue(result["is_llm_output"])

    async def test_provider_child_process(self):
        result = await self.service._run_inference("input")
        self.assertEqual(result["text"], "local response")

    async def test_job_cancel_reaps_active_provider_child(self):
        self.release.clear()
        job = (await self.service.handle(request("job_submit", text="cancel", mode="inference")))["result"]
        try:
            async def wait_for_request():
                while not self.received.is_set():
                    await asyncio.sleep(0.01)
            await asyncio.wait_for(wait_for_request(), timeout=3)
            self.assertTrue(multiprocessing.active_children())
            cancelled = await self.service.handle(request("job_cancel", job_id=job["id"]))
            self.assertEqual(cancelled["result"]["status"], "cancelled")
            await asyncio.wait_for(self.service.queue.join(), timeout=2)
            self.assertFalse(multiprocessing.active_children())
            self.assertIsNone((await self.service.handle(request("job_get", job_id=job["id"])))["result"]["result"])
        finally:
            self.release.set()

    async def test_parent_deadline_reaps_child(self):
        with patch("thox_usb.jobs.INFERENCE_DEADLINE_SECONDS", 0):
            with self.assertRaises(RequestError) as raised:
                await self.service._run_inference("input")
        self.assertEqual(raised.exception.code, "provider_timeout")
        # A subsequent process completes, demonstrating cleanup released resources.
        self.assertEqual((await self.service._run_inference("input"))["text"], "local response")

    async def test_provider_redirect_is_rejected(self):
        self.reply["status"] = 302
        with self.assertRaises(RequestError) as raised:
            self.service._infer("private")
        self.assertEqual(raised.exception.code, "provider_redirect")

    async def test_provider_size_and_encrypted_output_limits(self):
        self.reply["body"] = b"x" * 262145
        with self.assertRaises(RequestError) as raised:
            self.service._infer("input")
        self.assertEqual(raised.exception.code, "provider_response_too_large")
        # Raw response fits its limit but would overflow the encrypted envelope.
        self.reply["body"] = json.dumps({"choices": [{"message": {"content": "\0" * 23000}}]}).encode()
        with self.assertRaises(RequestError) as raised:
            self.service._infer("input")
        self.assertEqual(raised.exception.code, "provider_response_too_large")

    async def test_provider_errors_are_sanitized(self):
        self.reply["body"] = b"secret debug error"
        with self.assertRaises(RequestError) as raised:
            self.service._infer("input")
        self.assertEqual(raised.exception.code, "provider_invalid_response")
        self.assertNotIn("secret", raised.exception.message)

    def test_endpoint_scope(self):
        for url in ["http://localhost/v1/chat/completions", "https://evil.example/v1/chat/completions",
                    "http://127.0.0.1.evil/v1/chat/completions", "http://127.0.0.1/v1/chat/completions?x=1",
                    "http://user:pass@127.0.0.1/v1/chat/completions", "ftp://127.0.0.1/v1/chat/completions",
                    "http://192.168.1.2/v1/chat/completions", "http://[::1]/anything"]:
            with self.assertRaises(ValueError, msg=url):
                validate_inference_url(url)
        self.assertEqual(validate_inference_url("http://[::1]:8080/v1/chat/completions"), "http://[::1]:8080/v1/chat/completions")


if __name__ == "__main__":
    unittest.main()
