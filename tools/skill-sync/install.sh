#!/usr/bin/env bash
# Symlink skill-sync into ~/.local/bin so it runs from anywhere.
# Usage: ./install.sh        (undo with ./uninstall.sh)
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/bin/skill-sync.js"
BIN="$HOME/.local/bin"
LINK="$BIN/skill-sync"

command -v node >/dev/null || { echo "node (>=20) is required" >&2; exit 1; }

command -v npm >/dev/null || { echo "npm is required" >&2; exit 1; }
# pinned `skills` CLI (fast, version-locked); skill-sync always uses this local copy
(cd "$(dirname "$SRC")/.." && npm install --no-audit --no-fund --silent)

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
