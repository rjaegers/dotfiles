#!/usr/bin/env python3
"""Install verified release binaries for Linux, without system packages."""

import hashlib
import json
import os
import platform
import tarfile
import tempfile
import urllib.request
from pathlib import Path


TOOLS = (
    ("starship", "starship/starship", "starship-{arch}-unknown-linux-musl.tar.gz"),
    ("eza", "eza-community/eza", "eza_{arch}-unknown-linux-gnu.tar.gz"),
    ("bat", "sharkdp/bat", "bat-{tag}-{arch}-unknown-linux-gnu.tar.gz"),
    ("fd", "sharkdp/fd", "fd-{tag}-{arch}-unknown-linux-gnu.tar.gz"),
    ("rg", "BurntSushi/ripgrep", "ripgrep-{version}-{arch}-unknown-linux-musl.tar.gz"),
    ("zoxide", "ajeetdsouza/zoxide", "zoxide-{version}-{arch}-unknown-linux-musl.tar.gz"),
    ("dust", "bootandy/dust", "dust-{tag}-{arch}-unknown-linux-gnu.tar.gz"),
    ("delta", "dandavison/delta", "delta-{version}-{arch}-unknown-linux-gnu.tar.gz"),
)


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": "rjaegers-dotfiles"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def install(name, repository, asset_pattern, arch, bin_dir):
    destination = bin_dir / name
    if destination.is_file() and os.access(destination, os.X_OK):
        print(f"{name}: already installed at {destination}", flush=True)
        return

    release = json.loads(
        download(f"https://api.github.com/repos/{repository}/releases/latest")
    )
    version = release["tag_name"].removeprefix("v")
    asset_name = asset_pattern.format(version=version, tag=release["tag_name"], arch=arch)
    asset = next(
        (item for item in release["assets"] if item["name"] == asset_name), None
    )
    if asset is None or not (asset.get("digest") or "").startswith("sha256:"):
        raise RuntimeError(f"{repository} has no verified release asset {asset_name}")

    print(f"{name}: downloading {release['tag_name']}", flush=True)
    archive = download(asset["browser_download_url"])
    expected = asset["digest"].removeprefix("sha256:")
    if hashlib.sha256(archive).hexdigest() != expected:
        raise RuntimeError(f"{name}: release checksum mismatch")

    with tempfile.TemporaryFile() as compressed:
        compressed.write(archive)
        compressed.seek(0)
        with tarfile.open(fileobj=compressed, mode="r:gz") as tar:
            candidates = [
                member
                for member in tar.getmembers()
                if member.isfile() and Path(member.name).name == name
            ]
            if len(candidates) != 1:
                raise RuntimeError(f"{name}: expected one binary in {asset_name}")
            binary = tar.extractfile(candidates[0])
            if binary is None:
                raise RuntimeError(f"{name}: cannot read binary from {asset_name}")
            with tempfile.NamedTemporaryFile(dir=bin_dir, delete=False) as output:
                temporary = Path(output.name)
                try:
                    while chunk := binary.read(1024 * 1024):
                        output.write(chunk)
                    output.flush()
                    os.fchmod(output.fileno(), 0o755)
                    os.replace(temporary, destination)
                finally:
                    temporary.unlink(missing_ok=True)


def main():
    if platform.system() != "Linux":
        raise RuntimeError("This dotfiles installer supports Linux only")
    arch = platform.machine()
    if arch not in ("x86_64", "aarch64"):
        raise RuntimeError(f"Unsupported Linux architecture: {arch}")
    bin_dir = Path(os.environ.get("XDG_BIN_HOME", Path.home() / ".local/bin")).expanduser()
    bin_dir.mkdir(parents=True, exist_ok=True)
    for tool in TOOLS:
        install(*tool, arch, bin_dir)


if __name__ == "__main__":
    main()
