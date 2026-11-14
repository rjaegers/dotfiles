import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("install_tools", ROOT / "scripts/install-tools.py")
install_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(install_tools)


def release(tag, script):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        info = tarfile.TarInfo(f"fd-{tag}/fd")
        info.size = len(script)
        archive.addfile(info, io.BytesIO(script))
    data = buffer.getvalue()
    asset = {
        "name": f"fd-{tag}-x86_64-unknown-linux-gnu.tar.gz",
        "digest": f"sha256:{hashlib.sha256(data).hexdigest()}",
        "browser_download_url": f"https://example.test/{tag}",
    }
    return {"tag_name": tag, "assets": [asset]}, data


class FdFallbackTests(unittest.TestCase):
    def install(self, directory):
        install_tools.install(
            "fd", "sharkdp/fd",
            "fd-{tag}-{arch}-unknown-linux-gnu.tar.gz", "x86_64", directory,
        )

    def test_uses_latest_when_it_runs(self):
        latest, archive = release("v2", b"#!/bin/sh\nexit 0\n")
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(install_tools, "download", side_effect=[json.dumps(latest).encode(), archive]) as download:
                self.install(Path(directory))
            self.assertEqual((Path(directory) / "fd").read_bytes(), b"#!/bin/sh\nexit 0\n")
            self.assertEqual(download.call_count, 2)

    def test_falls_back_when_latest_cannot_run(self):
        latest, broken = release("v2", b"#!/bin/sh\nexit 1\n")
        previous, working = release("v1", b"#!/bin/sh\nexit 0\n")
        responses = [
            json.dumps(latest).encode(), broken,
            json.dumps([latest, previous]).encode(), working,
        ]
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(install_tools, "download", side_effect=responses):
                self.install(Path(directory))
            self.assertEqual((Path(directory) / "fd").read_bytes(), b"#!/bin/sh\nexit 0\n")

    def test_does_not_install_when_all_releases_fail(self):
        latest, broken = release("v2", b"#!/bin/sh\nexit 1\n")
        responses = [json.dumps(latest).encode(), broken, json.dumps([latest]).encode()]
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(install_tools, "download", side_effect=responses):
                with self.assertRaisesRegex(RuntimeError, "no compatible"):
                    self.install(Path(directory))
            self.assertFalse((Path(directory) / "fd").exists())

    def test_checksum_failure_does_not_trigger_fallback(self):
        latest, _ = release("v2", b"#!/bin/sh\nexit 0\n")
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(install_tools, "download", side_effect=[json.dumps(latest).encode(), b"bad"]):
                with self.assertRaisesRegex(RuntimeError, "checksum mismatch"):
                    self.install(Path(directory))
            self.assertFalse((Path(directory) / "fd").exists())


if __name__ == "__main__":
    unittest.main()
