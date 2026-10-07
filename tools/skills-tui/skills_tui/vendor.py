"""Vendor (pure): parse `vendors.txt` lines, classify upstream skills against the lib, lock helpers.

`vendors.txt`: one `npx skills add <source> --skill <names...>` per line; `#` starts a comment;
a trailing `# bundle=<name>` picks the marketplace bundle for new skills.
"""
import json
import re
import shlex
from dataclasses import dataclass
from pathlib import Path

from .dirhash import diff_files, tree_hash

NEW, UNCHANGED, CHANGED, PROTECTED = "new", "unchanged", "changed", "protected"

_COMMENT = re.compile(r"(?:^|\s)#")
_BUNDLE = re.compile(r"#\s*bundle=(\S+)")
_IGNORED_FLAGS = {"-g", "--global", "-y", "--yes", "--copy"}  # sandbox forces project scope, non-interactive
_IGNORED_VALUE_FLAGS = {"-a", "--agent"}
_SKILL_FLAGS = {"-s", "--skill"}
_SKILL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*$")
_SCRIPT_SUFFIXES = {".sh", ".bash", ".zsh", ".py", ".js", ".mjs", ".cjs", ".ts", ".rb", ".pl", ".ps1", ".bat", ".cmd"}


class VendorError(ValueError):
    def __init__(self, lineno: int, msg: str):
        super().__init__(f"line {lineno}: {msg}")


@dataclass(frozen=True)
class VendorLine:
    lineno: int
    source: str
    skills: tuple[str, ...]
    bundle: str | None
    ignored: tuple[str, ...]


def _parse_line(lineno: int, raw: str) -> VendorLine | None:
    m = _COMMENT.search(raw)
    code = raw[: m.start()] if m else raw
    if not code.strip():
        return None
    bundle = (_BUNDLE.search(raw[m.start():]) or [None, None])[1] if m else None
    try:
        toks = shlex.split(code)
    except ValueError as e:
        raise VendorError(lineno, f"unparseable: {e}") from e
    if toks[0] != "npx":
        raise VendorError(lineno, "only `npx skills add ...` lines are allowed")
    i = 1
    while i < len(toks) and toks[i].startswith("-"):  # npx's own flags (--yes)
        i += 1
    if toks[i:i + 2] not in (["skills", "add"], ["skills", "a"]):
        raise VendorError(lineno, "only `npx skills add ...` lines are allowed")
    toks = toks[i + 2:]

    source, skills, ignored, j = None, [], [], 0
    while j < len(toks):
        t = toks[j]
        if t in _IGNORED_FLAGS:
            ignored.append(t)
        elif t in _SKILL_FLAGS | _IGNORED_VALUE_FLAGS:
            vals = []
            while j + 1 < len(toks) and not toks[j + 1].startswith("-"):
                j += 1
                vals.append(toks[j])
            if t in _SKILL_FLAGS:
                skills += vals
            else:
                ignored += [t, *vals]
        elif t.startswith("-"):
            raise VendorError(lineno, f"unsupported flag {t}")
        elif source is None:
            source = t
        else:
            raise VendorError(lineno, f"unexpected argument {t!r}")
        j += 1
    if source is None:
        raise VendorError(lineno, "missing source (owner/repo or URL)")
    if not skills:
        raise VendorError(lineno, "missing --skill <names> (explicit names required)")
    if "*" in skills:
        raise VendorError(lineno, "--skill * not allowed; list skill names")
    bad = [n for n in skills if not _SKILL_NAME.match(n)]
    if bad:
        raise VendorError(lineno, f"invalid skill name {bad[0]!r}")
    return VendorLine(lineno, source, tuple(skills), bundle, tuple(ignored))


def parse_vendors(text: str) -> list[VendorLine]:
    lines = (_parse_line(n, raw) for n, raw in enumerate(text.splitlines(), 1))
    return [v for v in lines if v]


@dataclass(frozen=True)
class Change:
    name: str
    status: str
    detail: str = ""
    changed: tuple[str, ...] = ()   # files differing (CHANGED)
    added: tuple[str, ...] = ()     # files only upstream
    removed: tuple[str, ...] = ()   # files only in lib
    risky: tuple[str, ...] = ()     # scripts/executables among incoming files


def risky_files(d: Path, only: set[str] | None = None) -> tuple[str, ...]:
    out = []
    for p in sorted(d.rglob("*")):
        rel = p.relative_to(d).as_posix()
        if p.is_file() and (only is None or rel in only):
            if p.suffix.lower() in _SCRIPT_SUFFIXES or p.stat().st_mode & 0o111:
                out.append(rel)
    return tuple(out)


def classify(name: str, incoming: Path, entry: dict, lib: Path, lib_lock: dict) -> Change:
    """Compare an upstream skill dir (from the sandbox) with the lib's copy."""
    dest = lib / "skills" / name
    if not dest.exists():
        return Change(name, NEW, "not in lib", added=tuple(sorted(p.relative_to(incoming).as_posix() for p in incoming.rglob("*") if p.is_file())), risky=risky_files(incoming))
    owner = lib_lock.get(name)
    if owner is None:
        return Change(name, PROTECTED, "exists in lib and is not vendored (your own skill)")
    if owner.get("source") != entry.get("source"):
        return Change(name, PROTECTED, f"vendored from a different source ({owner.get('source')})")
    if tree_hash(dest) == tree_hash(incoming):
        return Change(name, UNCHANGED)
    changed, removed, added = diff_files(dest, incoming)  # a=lib, b=incoming
    incoming_files = set(changed) | set(added)
    return Change(name, CHANGED, "upstream differs", tuple(changed), tuple(added), tuple(removed), risky_files(incoming, incoming_files))


def read_lib_lock(lib: Path) -> dict:
    p = lib / "skills-lock.json"
    return json.loads(p.read_text()).get("skills", {}) if p.is_file() else {}


def write_lib_lock(lib: Path, skills: dict) -> None:
    """Same format as npx skills writes (sorted keys, indent 2, trailing newline): merges give 1-line diffs."""
    body = {"version": 1, "skills": dict(sorted(skills.items()))}
    (lib / "skills-lock.json").write_text(json.dumps(body, indent=2) + "\n")
