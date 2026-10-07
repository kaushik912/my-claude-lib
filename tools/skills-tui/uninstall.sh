#!/usr/bin/env bash
# Removes the skills-tui symlink (only if it points here) and the .venv.
# Never touches the lib's skills or any project's installed skills.
# Env: BIN_DIR (link dir), SKIP_DEPS=1 (keep .venv; for tests).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LINK="${BIN_DIR:-${HOME}/.local/bin}/skills-tui"

if [ -L "$LINK" ]; then
  if [ "$(readlink "$LINK")" = "${SCRIPT_DIR}/skills-tui" ]; then
    rm "$LINK" && echo "removed $LINK"
  else
    echo "refusing: $LINK points elsewhere ($(readlink "$LINK"))" >&2
    exit 1
  fi
else
  echo "no link at $LINK"
fi
[ -n "${SKIP_DEPS:-}" ] || { rm -rf "${SCRIPT_DIR}/.venv" && echo "removed .venv"; }
