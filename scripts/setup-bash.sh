#!/usr/bin/env bash
set -euo pipefail

begin='# BEGIN rjaegers/dotfiles'
end='# END rjaegers/dotfiles'
rc="$HOME/.bashrc"
profile="$HOME/.bash_profile"
repo="$(cd "$(dirname "$0")/.." && pwd)"

# An older installation linked .bash_profile directly to the repository.
resolve_link() {
    python3 -c 'import pathlib, sys; print(pathlib.Path(sys.argv[1]).resolve())' "$1"
}

if [[ -L "$profile" && "$(resolve_link "$profile")" == "$repo/configs/bash/bash-profile" ]]; then
    rm "$profile"
fi
if [[ -L "$HOME/.bash_aliases" && "$(resolve_link "$HOME/.bash_aliases")" == "$repo/configs/bash/bash-aliases" ]]; then
    rm "$HOME/.bash_aliases"
fi

append_block() {
    local path=$1
    local content=$2
    if [[ -e "$path" && ! -f "$path" ]]; then
        printf 'Cannot configure non-file %s\n' "$path" >&2
        return 1
    fi
    if [[ -f "$path" ]] && grep -Fxq "$begin" "$path"; then
        grep -Fxq "$end" "$path" || { printf 'Incomplete dotfiles block in %s\n' "$path" >&2; return 1; }
        return
    fi
    printf '\n%s\n%s\n%s\n' "$begin" "$content" "$end" >> "$path"
}

content='if [[ -z "${DOTFILES_BASH_LOADED:-}" ]]; then
DOTFILES_BASH_LOADED=1
case ":$PATH:" in
  *":${XDG_BIN_HOME:-$HOME/.local/bin}:"*) ;;
  *) export PATH="${XDG_BIN_HOME:-$HOME/.local/bin}:$PATH" ;;
esac
export BAT_THEME="gruvbox-dark"
if [[ $- == *i* ]]; then
  [[ -f "$HOME/.bash_aliases" ]] && . "$HOME/.bash_aliases"
  . "$HOME/.config/rjaegers-dotfiles/bash-aliases"
  command -v zoxide >/dev/null && eval "$(zoxide init bash)"'
if [[ ! -f "$rc" ]] || ! grep -Fxq 'eval "$(starship init bash)"' "$rc"; then
    content="$content"'
  command -v starship >/dev/null && eval "$(starship init bash)"'
fi
content="$content"'
fi
fi'
append_block "$rc" "$content"

# A login shell must load .bashrc, but do not replace a user's existing profile.
# Without .bash_profile, Bash reads .profile (which usually sources .bashrc).
if [[ -e "$profile" ]]; then
    append_block "$profile" '[[ -f "$HOME/.bashrc" ]] && . "$HOME/.bashrc"'
elif [[ ! -e "$HOME/.bash_login" ]]; then
    append_block "$HOME/.profile" '[[ -f "$HOME/.bashrc" ]] && . "$HOME/.bashrc"'
fi
