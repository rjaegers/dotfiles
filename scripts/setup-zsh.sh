#!/usr/bin/env bash
set -euo pipefail

[[ "$(uname -s)" == Darwin ]] || exit 0

rc="$HOME/.zshrc"
begin='# BEGIN rjaegers/dotfiles'
end='# END rjaegers/dotfiles'
if [[ -e "$rc" && ! -f "$rc" ]]; then
    printf 'Cannot configure non-file %s\n' "$rc" >&2
    exit 1
fi
if [[ -f "$rc" ]] && grep -Fxq "$begin" "$rc"; then
    grep -Fxq "$end" "$rc" || { printf 'Incomplete dotfiles block in %s\n' "$rc" >&2; exit 1; }
    exit 0
fi

{
    printf '\n%s\n' "$begin"
    cat <<'EOF'
case ":$PATH:" in
  *":${XDG_BIN_HOME:-$HOME/.local/bin}:"*) ;;
  *) export PATH="${XDG_BIN_HOME:-$HOME/.local/bin}:$PATH" ;;
esac
export BAT_THEME="gruvbox-dark"
. "$HOME/.config/rjaegers-dotfiles/bash-aliases"
command -v zoxide >/dev/null && eval "$(zoxide init zsh)"
EOF
    if [[ ! -f "$rc" ]] || ! grep -Fxq 'eval "$(starship init zsh)"' "$rc"; then
        printf '%s\n' 'command -v starship >/dev/null && eval "$(starship init zsh)"'
    fi
    printf '%s\n' "$end"
} >> "$rc"
