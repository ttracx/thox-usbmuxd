# SPDX-License-Identifier: GPL-3.0-or-later
import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from thox_usb.__main__ import create_pair_key, loopback_host, parser, read_pair_key


class CliTests(unittest.TestCase):
    def test_pair_private_no_secret_by_default_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pair.key"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                create_pair_key(path)
            self.assertEqual(output.getvalue().strip(), str(path))
            self.assertEqual(len(read_pair_key(path)), 32)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            original = path.read_bytes()
            with self.assertRaises(FileExistsError):
                create_pair_key(path)
            self.assertEqual(path.read_bytes(), original)
            path.chmod(0o644)
            with self.assertRaises(ValueError):
                read_pair_key(path)

    def test_pair_reveal_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pair.key"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                create_pair_key(path, reveal=True)
            self.assertEqual(output.getvalue().splitlines()[1], path.read_text().strip())

    def test_pair_read_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, linked = Path(tmp) / "key", Path(tmp) / "linked"
            with contextlib.redirect_stdout(io.StringIO()):
                create_pair_key(path)
            linked.symlink_to(path)
            with self.assertRaises(OSError):
                read_pair_key(linked)

    def test_parser_loopback_port_and_retry_bounds(self):
        self.assertEqual(loopback_host("localhost"), "127.0.0.1")
        command = ["bridge", "--pair-key", "key", "--workspace", "jobs"]
        args = parser().parse_args(command)
        self.assertEqual(args.port, 49322)
        for invalid in [["--host", "0.0.0.0"], ["--host", "example.com"], ["--port", "65536"],
                        ["--reconnect", "nan"], ["--reconnect", "0"]]:
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                parser().parse_args(command + invalid)


if __name__ == "__main__":
    unittest.main()
