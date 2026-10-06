#!/usr/bin/env bash
# Symlink list-skills into ~/.local/bin so it runs from anywhere.
# Usage: ./install.sh        (undo with ./uninstall.sh)
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/list-skills"
BIN="$HOME/.local/bin"
LINK="$BIN/list-skills"

chmod +x "$SRC"
mkdir -p "$BIN"

if [ -e "$LINK" ] && [ ! -L "$LINK" ]; then
  echo "refusing: $LINK exists and is not a symlink" >&2
  exit 1
fi

ln -sfn "$SRC" "$LINK"
echo "linked $LINK -> $SRC"
case ":$PATH:" in
  *":$BIN:"*) ;;
  *) echo "note: $BIN is not on PATH" ;;
esac
