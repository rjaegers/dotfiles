#!/usr/bin/env python3
"""Install shell tools and verified Herdr release binaries."""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
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

MACOS_TOOLS = (
    ("starship", "starship"),
    ("eza", "eza"),
    ("bat", "bat"),
    ("fd", "fd"),
    ("rg", "ripgrep"),
    ("zoxide", "zoxide"),
    ("dust", "dust"),
    ("delta", "git-delta"),
    ("wget", "wget"),
)


def download(url):
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "download"
        subprocess.run(
            ["wget", "-q", "--timeout=120", "--tries=3", "-O", str(target), url],
            check=True,
        )
        return target.read_bytes()


def write_binary(name, binary, bin_dir):
    destination = bin_dir / name
    with tempfile.NamedTemporaryFile(dir=bin_dir, delete=False) as output:
        temporary = Path(output.name)
        try:
            output.write(binary)
            output.flush()
            os.fchmod(output.fileno(), 0o755)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)


def install_herdr(arch, bin_dir, system):
    destination = bin_dir / "herdr"
    manifest = json.loads(download("https://herdr.dev/latest.json"))
    target = f"{system}-{arch}"
    url = manifest["assets"][target]
    expected = manifest["sha256"][target]
    if len(expected) != 64 or any(digit not in "0123456789abcdef" for digit in expected.lower()):
        raise RuntimeError("herdr: invalid release checksum")
    if destination.is_file() and os.access(destination, os.X_OK):
        if hashlib.sha256(destination.read_bytes()).hexdigest() == expected.lower():
            print(f"herdr: already up to date at {destination}", flush=True)
            return
    if destination.is_symlink():
        raise RuntimeError(f"herdr: refusing to replace symlink {destination}; update its target manually")
    print(f"herdr: downloading {manifest['version']}", flush=True)
    binary = download(url)
    if hashlib.sha256(binary).hexdigest() != expected.lower():
        raise RuntimeError("herdr: release checksum mismatch")
    write_binary("herdr", binary, bin_dir)


def release_asset(release, asset_pattern, arch):
    version = release["tag_name"].removeprefix("v")
    asset_name = asset_pattern.format(version=version, tag=release["tag_name"], arch=arch)
    asset = next(
        (item for item in release["assets"] if item["name"] == asset_name), None
    )
    return asset_name, asset


def release_binary(name, repository, release, asset_pattern, arch):
    asset_name, asset = release_asset(release, asset_pattern, arch)
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
            return binary.read()


def executable_works(name, binary, bin_dir):
    with tempfile.TemporaryDirectory(dir=bin_dir) as directory:
        candidate = (Path(directory) / name).resolve()
        candidate.write_bytes(binary)
        candidate.chmod(0o755)
        try:
            result = subprocess.run(
                [str(candidate), "--version"], cwd=directory,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return result.returncode == 0


def install(name, repository, asset_pattern, arch, bin_dir):
    destination = bin_dir / name
    if destination.is_file() and os.access(destination, os.X_OK):
        print(f"{name}: already installed at {destination}", flush=True)
        return

    release = json.loads(
        download(f"https://api.github.com/repos/{repository}/releases/latest")
    )
    binary = release_binary(name, repository, release, asset_pattern, arch)
    if name == "fd" and not executable_works(name, binary, bin_dir):
        print(f"fd: {release['tag_name']} cannot run; looking for a compatible release", flush=True)
        releases = json.loads(
            download(f"https://api.github.com/repos/{repository}/releases?per_page=100")
        )
        for candidate in releases:
            if candidate["tag_name"] == release["tag_name"] or candidate.get("draft") or candidate.get("prerelease"):
                continue
            _, asset = release_asset(candidate, asset_pattern, arch)
            if not asset or not (asset.get("digest") or "").startswith("sha256:"):
                continue
            binary = release_binary(name, repository, candidate, asset_pattern, arch)
            if executable_works(name, binary, bin_dir):
                print(f"fd: using compatible release {candidate['tag_name']}", flush=True)
                break
        else:
            raise RuntimeError("fd: no compatible verified release found")
    write_binary(name, binary, bin_dir)


def main():
    system = platform.system()
    if system not in ("Darwin", "Linux"):
        raise RuntimeError(f"Unsupported operating system: {system}")
    arch = platform.machine()
    if system == "Darwin" and arch == "arm64":
        arch = "aarch64"
    if arch not in ("x86_64", "aarch64"):
        raise RuntimeError(f"Unsupported {system} architecture: {arch}")
    bin_dir = Path(os.environ.get("XDG_BIN_HOME", Path.home() / ".local/bin")).expanduser()

    if system == "Darwin":
        missing = [formula for command, formula in MACOS_TOOLS if not shutil.which(command)]
        if missing:
            if not shutil.which("brew"):
                raise RuntimeError("Install Homebrew first: https://brew.sh")
            subprocess.run(["brew", "install", *missing], check=True)
        bin_dir.mkdir(parents=True, exist_ok=True)
        install_herdr(arch, bin_dir, "macos")
        return
    bin_dir.mkdir(parents=True, exist_ok=True)
    for tool in TOOLS:
        install(*tool, arch, bin_dir)
    install_herdr(arch, bin_dir, "linux")


if __name__ == "__main__":
    main()
