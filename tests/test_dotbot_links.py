import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DotbotLinkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.env = {**os.environ, "HOME": str(self.home)}

    def link(self):
        return subprocess.run(
            [str(ROOT / "dotbot/bin/dotbot"), "-d", str(ROOT),
             "-c", "install.conf.yaml", "--only", "link"],
            cwd=ROOT, env=self.env, text=True, capture_output=True,
        )

    def test_links_relink_and_remain_idempotent(self):
        config = self.home / ".config"
        config.mkdir()
        old = self.home / "old-config"
        old.write_text("unchanged")
        (config / "starship.toml").symlink_to(old)
        for _ in range(2):
            result = self.link()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(old.read_text(), "unchanged")
        for destination, source in (
            (".config/starship.toml", "configs/starship/starship.toml"),
            (".config/eza/theme.yml", "eza-themes/themes/gruvbox-dark.yml"),
            (".config/rjaegers-dotfiles/bash-aliases", "configs/bash/bash-aliases"),
        ):
            self.assertEqual((self.home / destination).resolve(), (ROOT / source).resolve())

    def test_existing_file_is_not_overwritten(self):
        config = self.home / ".config"
        config.mkdir()
        existing = config / "starship.toml"
        existing.write_text("user config")
        result = self.link()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(existing.read_text(), "user config")

    @unittest.skipUnless(shutil.which("eza"), "eza is not installed")
    def test_listing_aliases_accept_directory_arguments(self):
        target = self.home / "directory with spaces"
        target.mkdir()
        (target / "entry").touch()
        aliases = ROOT / "configs/bash/bash-aliases"
        (self.home / ".zshrc").symlink_to(aliases)
        env = {**self.env, "ZDOTDIR": str(self.home)}
        for shell in ("bash", "zsh"):
            if not shutil.which(shell):
                continue
            for alias in ("ls", "ll", "l", "llm", "la", "lx", "lS", "lt"):
                with self.subTest(shell=shell, alias=alias):
                    command = [shell]
                    if shell == "bash":
                        command.extend(["--noprofile", "--rcfile", str(aliases)])
                    command.extend(["-ic", f"{alias} {shlex.quote(str(target))}"])
                    result = subprocess.run(command, env=env, text=True, capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
