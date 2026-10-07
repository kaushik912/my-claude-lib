"""Directory hashing compatible with `npx skills`' lock `computedHash`, plus a file-level diff.

Algorithm (reverse-engineered, verified against real locks): SHA-256 streamed over every
file under the dir, sorted by relative POSIX path (case-insensitive); each file contributes
its relative path bytes then its content bytes.
"""
import hashlib
from pathlib import Path


def _files(d: Path) -> list[Path]:
    return sorted((p for p in d.rglob("*") if p.is_file()), key=lambda p: p.relative_to(d).as_posix().casefold())


def tree_hash(d: Path) -> str:
    h = hashlib.sha256()
    for p in _files(d):
        h.update(p.relative_to(d).as_posix().encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def diff_files(a: Path, b: Path) -> tuple[list[str], list[str], list[str]]:
    """(changed, only_in_a, only_in_b) as relative paths."""
    fa = {p.relative_to(a).as_posix(): p for p in _files(a)}
    fb = {p.relative_to(b).as_posix(): p for p in _files(b)}
    changed = sorted(r for r in fa.keys() & fb.keys() if fa[r].read_bytes() != fb[r].read_bytes())
    return changed, sorted(fa.keys() - fb.keys()), sorted(fb.keys() - fa.keys())
