#!/usr/bin/env bash
# Remove the ~/.local/bin/list-skills symlink created by install.sh.
# Only removes it if it points at this folder's script; the script itself stays.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/list-skills"
LINK="$HOME/.local/bin/list-skills"

if [ ! -L "$LINK" ]; then
  echo "nothing to remove: $LINK is not a symlink"
  exit 0
fi

if [ "$(readlink "$LINK")" != "$SRC" ]; then
  echo "refusing: $LINK points elsewhere ($(readlink "$LINK"))" >&2
  exit 1
fi

rm "$LINK"
echo "removed $LINK"
