# Agent instructions

## Compatibility

- Support macOS (Apple silicon and Intel) and Linux devcontainers (arm64 and
  x86_64). Preserve Bash and macOS Zsh behavior.
- Keep installation repeatable. Extend existing shell startup files instead of
  replacing them; preserve user files, unrelated links and `XDG_BIN_HOME`.
- Use `wget`, not `curl`, for HTTP(S) downloads and fetches. Devcontainers may
  not have `curl`; keep Linux setups working without it.
- Install missing macOS tools with Homebrew. Keep Linux release downloads
  checksum-verified before installing binaries.
- Keep eza aliases compatible with directory arguments: use `--icons=always`,
  not a bare `--icons`. Test filenames containing spaces.
- Test new `fd` releases on both architectures, including x86 emulation on
  Apple silicon. Keep the verified fallback for releases that cannot start.

## Dependencies and Herdr

- Dotbot and eza themes are pinned Git submodules. Check their upstream
  revisions and test a fresh recursive checkout when updating them. Dotbot's
  bundled PyYAML is pinned by Dotbot itself; report outdated transitive pins
  rather than silently modifying the submodule checkout.
- Install and update Herdr TUI on both platforms from its checksummed official
  manifest. Do not restore the obsolete Herdr Projects plugin.
- Never stop or restart a running Herdr server without user approval: stopping
  it exits its panes. A newer client may require a server restart.

## Validation

- Run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`
  for installer changes. Exercise Linux and macOS paths where relevant.
- Test installer changes with an isolated home directory; don't run the full
  installer against the user's home merely to validate changes.
