"""Doctor (pure): compare a project's `skills-lock.json` entries with project copies and the lib.

Compares three hashes per entry: project dir, lib source dir, and the lock's `computedHash`.
Never writes anything; fixes are expressed as options and executed elsewhere via `npx skills`.
"""
import json
from dataclasses import dataclass
from pathlib import Path

from .dirhash import diff_files, tree_hash
from .kinds.skills import CANON_DIR, CLAUDE_DIR

LOCK = "skills-lock.json"
SUPPORTED_VERSION = 1

OUTDATED, MODIFIED, CONFLICT, LOCK_STALE = "outdated", "modified", "conflict", "lock-stale"
DANGLING, ORPHAN, DEAD_SOURCE, UNTRACKED = "dangling", "orphan", "dead-source", "untracked"
FOREIGN, CORRUPT = "foreign", "corrupt"
UNLINKED = "not-linked"

UPDATE, DELETE, KEEP = "update", "delete", "keep"


@dataclass(frozen=True)
class Issue:
    name: str
    state: str
    detail: str
    options: tuple[str, ...] = ()  # report-only when empty; else includes KEEP
    recommended: str | None = None  # only for clear-cut cases


class LockError(ValueError):
    pass


def read_lock(project: Path) -> dict[str, dict]:
    path = project / LOCK
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except ValueError as e:
        raise LockError(f"unreadable {LOCK}: {e}") from e
    if not isinstance(data, dict) or data.get("version") != SUPPORTED_VERSION or not isinstance(data.get("skills"), dict):
        raise LockError(f"unsupported {LOCK} format (expected version {SUPPORTED_VERSION})")
    return data["skills"]


def _diff_detail(proj: Path, src: Path) -> str:
    changed, extra, missing = diff_files(proj, src)
    parts = [f"{label}: {', '.join(files)}" for label, files in (("changed", changed), ("extra", extra), ("missing", missing)) if files]
    return "; ".join(parts) or "same files"


def _layout_issue(name: str, project: Path) -> Issue | None:
    """Content is healthy; check the layout: real files in .agents/skills, symlink in .claude/skills."""
    canon, link = project / CANON_DIR / name, project / CLAUDE_DIR / name
    if not (link.is_symlink() and link.resolve() == canon.resolve()):
        why = "missing" if not link.is_symlink() and not link.exists() else "not a symlink to .agents/skills"
        return Issue(name, UNLINKED, f".claude/skills/{name} {why}", (UPDATE, KEEP), UPDATE)
    return None


def _check_entry(name: str, ent: dict, project: Path, lib: Path) -> Issue | None:
    src_rel = ent.get("source")
    if ent.get("sourceType") != "local" or not isinstance(src_rel, str):
        return Issue(name, FOREIGN, f"{ent.get('sourceType', '?')} source, not checked")
    src_root = (project / src_rel).resolve()
    in_lib = (lib / "skills" / name / "SKILL.md").is_file()
    if not src_root.exists():
        opts = (UPDATE, KEEP) if in_lib else ()
        return Issue(name, DEAD_SOURCE, f"source {src_rel} not found", opts)
    if src_root != lib.resolve():
        return Issue(name, FOREIGN, "local source is a different lib, not checked")
    if not in_lib:
        return Issue(name, ORPHAN, "no longer in lib", (DELETE, KEEP), DELETE)
    src, proj = lib / "skills" / name, project / CANON_DIR / name
    if not proj.is_dir():
        return Issue(name, DANGLING, "in lock, missing from project", (UPDATE, DELETE, KEEP))
    h_lock, h_src, h_proj = ent.get("computedHash"), tree_hash(src), tree_hash(proj)
    if h_proj == h_src == h_lock:
        return _layout_issue(name, project)
    if h_proj == h_src:
        return Issue(name, LOCK_STALE, "project matches lib; lock hash is old", (UPDATE, KEEP), UPDATE)
    if h_proj == h_lock:
        return Issue(name, OUTDATED, f"lib changed since install ({_diff_detail(proj, src)})", (UPDATE, KEEP), UPDATE)
    if h_src == h_lock:
        return Issue(name, MODIFIED, f"project edited locally ({_diff_detail(proj, src)})", (UPDATE, KEEP))
    return Issue(name, CONFLICT, f"both changed ({_diff_detail(proj, src)})", (UPDATE, KEEP))


def diagnose(project: Path, lib: Path) -> list[Issue]:
    try:
        lock = read_lock(project)
    except LockError as e:
        return [Issue(LOCK, CORRUPT, str(e))]
    issues = [i for name, ent in sorted(lock.items()) if (i := _check_entry(name, ent, project, lib))]
    root = project / CANON_DIR
    for d in sorted(root.iterdir()) if root.is_dir() else []:
        if d.is_dir() and not d.is_symlink() and d.name not in lock and (lib / "skills" / d.name / "SKILL.md").is_file():
            issues.append(Issue(d.name, UNTRACKED, "in project, not in lock", (UPDATE, DELETE, KEEP)))
    return issues
