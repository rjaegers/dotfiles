import importlib.util
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("install_tools", ROOT / "scripts/install-tools.py")
install_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(install_tools)


class ToolInstallationTests(unittest.TestCase):
    def test_macos_installs_only_missing_homebrew_formulae(self):
        installed = {"brew", "starship", "eza", "bat", "fd", "zoxide", "dust"}
        with tempfile.TemporaryDirectory() as directory:
            with (
                mock.patch.object(install_tools.platform, "system", return_value="Darwin"),
                mock.patch.object(install_tools.platform, "machine", return_value="arm64"),
                mock.patch.dict(os.environ, {"XDG_BIN_HOME": directory}),
                mock.patch.object(install_tools.shutil, "which", side_effect=lambda name: name if name in installed else None),
                mock.patch.object(install_tools.subprocess, "run") as run,
                mock.patch.object(install_tools, "install") as install,
                mock.patch.object(install_tools, "install_devcontainer") as devcontainer,
                mock.patch.object(install_tools, "install_herdr") as herdr,
            ):
                install_tools.main()
            install.assert_called_once_with(
                "copilot",
                "github/copilot-cli",
                "copilot-darwin-arm64.tar.gz",
                "aarch64",
                Path(directory),
            )
            devcontainer.assert_called_once_with(Path(directory))
            herdr.assert_called_once_with("aarch64", Path(directory), "macos")
        run.assert_called_once_with(
            ["brew", "install", "ripgrep", "git-delta", "wget", "gh", "node"],
            check=True,
        )

    def test_linux_still_installs_verified_tools_and_herdr(self):
        with tempfile.TemporaryDirectory() as directory:
            with (
                mock.patch.object(install_tools.platform, "system", return_value="Linux"),
                mock.patch.object(install_tools.platform, "machine", return_value="aarch64"),
                mock.patch.dict(os.environ, {"XDG_BIN_HOME": directory}),
                mock.patch.object(install_tools, "install") as install,
                mock.patch.object(install_tools, "install_devcontainer") as devcontainer,
                mock.patch.object(install_tools, "install_herdr") as herdr,
            ):
                install_tools.main()
            self.assertEqual(install.call_count, len(install_tools.TOOLS) + 2)
            self.assertIn(
                mock.call(
                    "gh",
                    "cli/cli",
                    "gh_{version}_linux_arm64.tar.gz",
                    "aarch64",
                    Path(directory),
                ),
                install.call_args_list,
            )
            self.assertIn(
                mock.call(
                    "copilot",
                    "github/copilot-cli",
                    "copilot-linux-arm64.tar.gz",
                    "aarch64",
                    Path(directory),
                ),
                install.call_args_list,
            )
            devcontainer.assert_called_once_with(Path(directory))
            herdr.assert_called_once_with("aarch64", Path(directory), "linux")

    def test_devcontainer_installs_with_npm_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            with (
                mock.patch.object(install_tools.shutil, "which", return_value="/usr/bin/npm"),
                mock.patch.object(install_tools.subprocess, "run") as run,
            ):
                install_tools.install_devcontainer(Path(directory))
        run.assert_called_once_with(
            [
                "/usr/bin/npm",
                "install",
                "--global",
                "--prefix",
                directory,
                "@devcontainers/cli",
            ],
            check=True,
        )

    def test_devcontainer_requires_npm_when_not_already_installed(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(install_tools.shutil, "which", return_value=None):
                with self.assertRaisesRegex(RuntimeError, "npm is required"):
                    install_tools.install_devcontainer(Path(directory))

    def test_macos_herdr_release_selection_and_checksum(self):
        binary = b"herdr test binary"
        checksum = hashlib.sha256(binary).hexdigest()
        for arch in ("x86_64", "aarch64"):
            with self.subTest(arch=arch), tempfile.TemporaryDirectory() as directory:
                target = f"macos-{arch}"
                manifest = json.dumps({
                    "version": "test",
                    "assets": {target: f"https://example.test/{target}"},
                    "sha256": {target: checksum},
                }).encode()
                with mock.patch.object(install_tools, "download", side_effect=[manifest, binary]) as download:
                    install_tools.install_herdr(arch, Path(directory), "macos")
                self.assertEqual(download.call_args_list[1].args[0], f"https://example.test/{target}")
                self.assertEqual((Path(directory) / "herdr").read_bytes(), binary)
                self.assertTrue(os.access(Path(directory) / "herdr", os.X_OK))

    def test_bad_herdr_checksum_is_rejected(self):
        manifest = json.dumps({
            "version": "test",
            "assets": {"macos-aarch64": "https://example.test/herdr"},
            "sha256": {"macos-aarch64": "0" * 64},
        }).encode()
        with tempfile.TemporaryDirectory() as directory:
            current = Path(directory) / "herdr"
            current.write_bytes(b"old")
            current.chmod(0o755)
            with mock.patch.object(install_tools, "download", side_effect=[manifest, b"wrong"]):
                with self.assertRaisesRegex(RuntimeError, "checksum mismatch"):
                    install_tools.install_herdr("aarch64", Path(directory), "macos")
            self.assertEqual(current.read_bytes(), b"old")

    def test_existing_latest_herdr_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "herdr"
            binary.write_bytes(b"existing")
            binary.chmod(0o755)
            manifest = json.dumps({
                "version": "test",
                "assets": {"macos-aarch64": "https://example.test/herdr"},
                "sha256": {"macos-aarch64": hashlib.sha256(b"existing").hexdigest()},
            }).encode()
            with mock.patch.object(install_tools, "download", return_value=manifest) as download:
                install_tools.install_herdr("aarch64", Path(directory), "macos")
            download.assert_called_once_with("https://herdr.dev/latest.json")
            self.assertEqual(binary.read_bytes(), b"existing")

    def test_outdated_herdr_is_updated(self):
        latest = b"latest release"
        manifest = json.dumps({
            "version": "test",
            "assets": {"macos-aarch64": "https://example.test/herdr"},
            "sha256": {"macos-aarch64": hashlib.sha256(latest).hexdigest()},
        }).encode()
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "herdr"
            binary.write_bytes(b"old release")
            binary.chmod(0o755)
            with mock.patch.object(install_tools, "download", side_effect=[manifest, latest]):
                install_tools.install_herdr("aarch64", Path(directory), "macos")
            self.assertEqual(binary.read_bytes(), latest)
            self.assertTrue(os.access(binary, os.X_OK))

    def test_outdated_herdr_symlink_is_not_replaced(self):
        manifest = json.dumps({
            "version": "test",
            "assets": {"macos-aarch64": "https://example.test/herdr"},
            "sha256": {"macos-aarch64": "0" * 64},
        }).encode()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "managed-herdr"
            target.write_bytes(b"old")
            target.chmod(0o755)
            binary = Path(directory) / "herdr"
            binary.symlink_to(target)
            with mock.patch.object(install_tools, "download", return_value=manifest):
                with self.assertRaisesRegex(RuntimeError, "refusing to replace symlink"):
                    install_tools.install_herdr("aarch64", Path(directory), "macos")
            self.assertTrue(binary.is_symlink())
            self.assertEqual(target.read_bytes(), b"old")

    def test_unsupported_macos_architecture_fails_before_installing(self):
        with (
            mock.patch.object(install_tools.platform, "system", return_value="Darwin"),
            mock.patch.object(install_tools.platform, "machine", return_value="unknown"),
            mock.patch.object(install_tools.subprocess, "run") as run,
        ):
            with self.assertRaisesRegex(RuntimeError, "Unsupported Darwin architecture"):
                install_tools.main()
            run.assert_not_called()

    def test_macos_requires_homebrew_for_missing_tools(self):
        with (
            mock.patch.object(install_tools.platform, "system", return_value="Darwin"),
            mock.patch.object(install_tools.shutil, "which", return_value=None),
        ):
            with self.assertRaisesRegex(RuntimeError, "Homebrew"):
                install_tools.main()


@unittest.skipUnless(platform.system() == "Darwin", "macOS integration test")
class DotbotIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.home = root / "home"
        self.home.mkdir()
        bin_dir = root / "bin"
        bin_dir.mkdir()
        for command, _ in install_tools.MACOS_TOOLS:
            executable = bin_dir / command
            executable.write_text(
                '#!/bin/sh\nif [ "$1" = "-qO-" ]; then printf "203.0.113.1\\n"; '
                'else cp "$HOME/manifest.json" "$5"; fi\n' if command == "wget"
                else "#!/bin/sh\nexit 0\n"
            )
            executable.chmod(0o755)
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
            "XDG_BIN_HOME": str(self.home / ".local/bin"),
        }
        local_bin = self.home / ".local/bin"
        local_bin.mkdir(parents=True)
        herdr = local_bin / "herdr"
        herdr.write_text("#!/bin/sh\nexit 1\n")
        herdr.chmod(0o755)
        for command in ("copilot", "devcontainer"):
            executable = local_bin / command
            executable.write_text("#!/bin/sh\nexit 0\n")
            executable.chmod(0o755)
        checksum = hashlib.sha256(herdr.read_bytes()).hexdigest()
        (self.home / "manifest.json").write_text(json.dumps({
            "version": "test",
            "assets": {f"macos-{arch}": "https://example.test/herdr" for arch in ("aarch64", "x86_64")},
            "sha256": {f"macos-{arch}": checksum for arch in ("aarch64", "x86_64")},
        }))

    def dotbot(self):
        return subprocess.run(
            [str(ROOT / "dotbot/bin/dotbot"), "-d", str(ROOT), "-c", "install.conf.yaml"],
            cwd=ROOT,
            env=self.env,
            text=True,
            capture_output=True,
        )

    def test_dotbot_configures_both_shells_without_overwriting_existing_setup(self):
        zshrc = self.home / ".zshrc"
        zshrc.write_text('export EXISTING_SETTING=yes\neval "$(starship init zsh)"\n')
        bashrc = self.home / ".bashrc"
        bashrc.write_text('eval "$(starship init bash)"\n')
        for _ in range(2):
            result = self.dotbot()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("export EXISTING_SETTING=yes", zshrc.read_text())
        self.assertEqual(zshrc.read_text().count('eval "$(starship init zsh)"'), 1)
        self.assertEqual(bashrc.read_text().count('eval "$(starship init bash)"'), 1)
        self.assertEqual(zshrc.read_text().count("# BEGIN rjaegers/dotfiles"), 1)
        self.assertEqual(bashrc.read_text().count("# BEGIN rjaegers/dotfiles"), 1)
        for path in (".config/starship.toml", ".config/eza/theme.yml", ".config/rjaegers-dotfiles/bash-aliases"):
            self.assertTrue((self.home / path).is_file())
        for shell, command in (("zsh", ["zsh", "-ic", "alias ls; ip"]), ("bash", ["bash", "--rcfile", str(bashrc), "-ic", "alias ls; ip"])):
            result = subprocess.run(command, env=self.env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, f"{shell}: {result.stderr}")
            self.assertIn("eza", result.stdout)
            self.assertIn("203.0.113.1", result.stdout)

    def test_bash_migrates_old_managed_symlinks_on_macos(self):
        (self.home / ".bash_profile").symlink_to(ROOT / "configs/bash/bash-profile")
        (self.home / ".bash_aliases").symlink_to(ROOT / "configs/bash/bash-aliases")
        result = self.dotbot()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.home / ".bash_profile").is_symlink())
        self.assertFalse((self.home / ".bash_aliases").is_symlink())
        self.assertIn(".bashrc", (self.home / ".profile").read_text())

    def test_incomplete_zsh_block_is_reported(self):
        zshrc = self.home / ".zshrc"
        zshrc.write_text("# BEGIN rjaegers/dotfiles\nexisting content\n")
        result = self.dotbot()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Incomplete dotfiles block", result.stdout + result.stderr)
        self.assertEqual(zshrc.read_text(), "# BEGIN rjaegers/dotfiles\nexisting content\n")

    def test_existing_herdr_projects_is_not_run(self):
        plugin = self.home / ".local/bin/herdr-projects"
        plugin.write_text('#!/bin/sh\nprintf "%s" "$1" > "$HOME/plugin-argument"\n')
        plugin.chmod(0o755)
        result = self.dotbot()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.home / "plugin-argument").exists())


if __name__ == "__main__":
    unittest.main()
