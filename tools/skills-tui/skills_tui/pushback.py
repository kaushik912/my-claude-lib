"""Push a drifted project skill back into the lib (own skills only; the caller enforces that).

File-level, not a dir swap: changed + added files are copied; files deleted in the project are NOT
propagated. Skipped for safety: symlinks, and anything the lib's .gitignore covers (credential files like
db.cnf would otherwise sit in the lib dir and be copied into every project by `npx skills add <lib>`).
"""
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .dirhash import diff_files
from .kinds.skills import CANON_DIR


class PushError(ValueError):
    pass


@dataclass(frozen=True)
class PushPlan:
    name: str
    src: Path                 # project's real skill dir
    dest: Path                # lib/skills/<name>
    copy: tuple[str, ...]     # relative paths to copy (changed + added)
    added: tuple[str, ...]    # subset of copy that is new in the lib
    not_propagated: tuple[str, ...]   # deleted in the project; left alone in the lib
    skipped: tuple[tuple[str, str], ...]  # (path, reason)

    def lines(self) -> list[str]:
        out = [f"    copy to lib: {', '.join(self.copy)}" + (f" (new: {', '.join(self.added)})" if self.added else "")]
        if self.not_propagated:
            out.append(f"    not propagated (deleted in project): {', '.join(self.not_propagated)}")
        out += [f"    skipped {p}: {why}" for p, why in self.skipped]
        return out


def _ignored(lib: Path, rel_in_lib: str) -> bool:
    r = subprocess.run(["git", "-C", str(lib), "check-ignore", "-q", "--", rel_in_lib], capture_output=True, text=True)
    if r.returncode in (0, 1):
        return r.returncode == 0
    raise PushError(f"cannot check the lib's .gitignore (is {lib} a git repo?): {r.stderr.strip()}")


def plan_push(project: Path, lib: Path, name: str) -> PushPlan:
    src, dest = project / CANON_DIR / name, lib / "skills" / name
    if not src.is_dir() or not dest.is_dir():
        raise PushError(f"{name}: needs both {src} and {dest}")
    changed, only_project, only_lib = diff_files(src, dest)
    copy, skipped = [], []
    for rel in [*changed, *only_project]:
        if (src / rel).is_symlink():
            skipped.append((rel, "symlink"))
        elif _ignored(lib, f"skills/{name}/{rel}"):
            skipped.append((rel, "ignored by the lib's .gitignore"))
        else:
            copy.append(rel)
    if not copy:
        raise PushError(f"{name}: nothing to push" + (f" (skipped: {', '.join(p for p, _ in skipped)})" if skipped else ""))
    added = tuple(r for r in copy if r in only_project)
    return PushPlan(name, src, dest, tuple(copy), added, tuple(only_lib), tuple(skipped))


def apply_push(plan: PushPlan) -> None:
    """Per-file copy via a temp sibling + atomic replace; verifies content afterwards."""
    for rel in plan.copy:
        target = plan.dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(f".{target.name}.push-tmp")
        shutil.copy2(plan.src / rel, tmp)
        os.replace(tmp, target)
        if target.read_bytes() != (plan.src / rel).read_bytes():
            raise PushError(f"{plan.name}: verify failed for {rel}")
