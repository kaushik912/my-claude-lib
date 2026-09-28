#!/usr/bin/env bash
# Creates a venv with deps and symlinks the `my-pick` launcher into ~/.local/bin (on PATH).
# Re-run after moving/re-cloning the repo — the link self-corrects.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"

python3 -m venv "${SCRIPT_DIR}/.venv" 2>/dev/null || { [ -x "${SCRIPT_DIR}/.venv/bin/python" ] || { echo "venv failed — try: sudo apt install python3-venv" >&2; exit 1; }; }
"${SCRIPT_DIR}/.venv/bin/pip" install -q -r "${SCRIPT_DIR}/requirements.txt"

mkdir -p "$BIN_DIR"
ln -sfn "${SCRIPT_DIR}/my-pick" "${BIN_DIR}/my-pick"
echo "Linked ${BIN_DIR}/my-pick -> ${SCRIPT_DIR}/my-pick"
case ":$PATH:" in *":${BIN_DIR}:"*) ;; *) echo "NOTE: add ${BIN_DIR} to PATH" ;; esac
