#!/usr/bin/env bash
set -euo pipefail

bin_dir="${XDG_BIN_HOME:-$HOME/.local/bin}"
mkdir -p "$bin_dir"
export PATH="$bin_dir:$PATH"

if [[ ! -x "$bin_dir/herdr" ]]; then
    printf 'Herdr binary missing; run the tool installation step first\n' >&2
    exit 1
fi

if [[ ! -x "$bin_dir/herdr-projects" ]]; then
    herdr plugin install eliasstravik/herdr-projects
fi
"$bin_dir/herdr-projects" configure
