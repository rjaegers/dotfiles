# Dotfiles

Run `./install` from this Git checkout on macOS or x86_64/aarch64 Linux.
Git, Python 3, Bash and network access are required. Dotbot checks out
the pinned `dotbot` and `eza-themes` submodules and links the Gruvbox Dark
Starship and eza themes. Existing shell startup files are extended, not replaced.
An existing
`~/.bash_aliases` is also left untouched. Open a new Bash shell after
installation.

On macOS, install [Homebrew](https://brew.sh/) and add it to your PATH first.
Missing tools, including `wget`, are installed using Homebrew. Both the default Zsh and Bash are
configured; open a new shell after installation. Herdr setup is Linux-only
and is skipped on macOS. A Nerd Font is recommended for the prompt and icons.

On Linux, `wget` is required, and tools are installed into
`${XDG_BIN_HOME:-~/.local/bin}`.

The installer provides Starship, eza (`ls`), bat (`cat`), fd (`find`), ripgrep
(`grep`), zoxide (`cd` via `z`), dust (`du`), and delta (`diff`). Apart from
the existing `ls` family of aliases, use these tools by their own names rather
than silently changing standard command semantics. On Linux, release assets are checked
against GitHub's SHA-256 digests before installation. Already installed
executables in the local bin directory are left alone; remove one and rerun
`./install` to update it. The eza theme and Starship palette use Gruvbox Dark;
`BAT_THEME` is set to `gruvbox-dark`.

On Linux, Herdr is installed from the checksummed [official release manifest](https://herdr.dev/latest.json)
and [Herdr Projects](https://github.com/eliasstravik/herdr-projects) is
installed and configured as a Herdr plugin. This step requires a working
Herdr installation and may need its server running; if it fails, start Herdr
and rerun `./install`. It does not create a project or launch an agent.
The plugin executes its upstream installation script; review the source
before running the setup on a machine you do not trust. Herdr Projects may
use its own download tooling internally; this repository's downloads use `wget`.

Starship and zoxide load from `~/.bashrc` in interactive Bash shells, so ordinary
terminal tabs and login shells receive the same setup. The installer removes
the old dotfiles-managed `~/.bash_profile` and `~/.bash_aliases` symlinks and
configures the existing login profile to source `.bashrc`.
Other existing profile content is preserved. The managed blocks are added
only once, so rerunning the installer is safe.

The latest `fd` release is checked before installation; if it cannot start
(for example, under x86 emulation), the installer tries earlier verified
releases and uses the newest one that works.
