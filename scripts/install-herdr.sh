#!/usr/bin/env bash
set -euo pipefail

bin_dir="${XDG_BIN_HOME:-$HOME/.local/bin}"
mkdir -p "$bin_dir"
export PATH="$bin_dir:$PATH"

if [[ ! -x "$bin_dir/herdr" ]]; then
    installer="$(mktemp)"
    trap 'rm -f "$installer"' EXIT
    curl -fsSL https://herdr.dev/install.sh -o "$installer"
    HERDR_INSTALL_DIR="$bin_dir" sh "$installer"
fi

if [[ ! -x "$bin_dir/herdr-projects" ]]; then
    herdr plugin install eliasstravik/herdr-projects
fi
"$bin_dir/herdr-projects" configure
