#!/usr/bin/env bash
# Creates a venv with deps and symlinks the `skills-tui` launcher into ~/.local/bin.
# Env: BIN_DIR (link dir), SKIP_DEPS=1 (no venv/pip; for tests). Re-run to refresh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${BIN_DIR:-${HOME}/.local/bin}"

if [ -z "${SKIP_DEPS:-}" ]; then
  python3 -m venv "${SCRIPT_DIR}/.venv" 2>/dev/null || { [ -x "${SCRIPT_DIR}/.venv/bin/python" ] || { echo "venv failed — try: sudo apt install python3-venv" >&2; exit 1; }; }
  "${SCRIPT_DIR}/.venv/bin/pip" install -q -r "${SCRIPT_DIR}/requirements.txt"
  command -v npx >/dev/null || echo "NOTE: npx not found — needed to install skills (install Node >=18)"
fi

mkdir -p "$BIN_DIR"
ln -sfn "${SCRIPT_DIR}/skills-tui" "${BIN_DIR}/skills-tui"
echo "Linked ${BIN_DIR}/skills-tui -> ${SCRIPT_DIR}/skills-tui"
case ":$PATH:" in *":${BIN_DIR}:"*) ;; *) echo "NOTE: add ${BIN_DIR} to PATH" ;; esac
