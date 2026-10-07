"""The only module that shells out: turns a Plan into `npx skills` calls."""
import subprocess
from pathlib import Path

from .plan import Plan


def build_commands(plan: Plan, lib: Path, agent: str = "claude-code", global_: bool = False) -> list[list[str]]:
    scope = ["-g"] if global_ else []
    cmds = []
    if plan.to_add:
        cmds.append(["npx", "--yes", "skills", "add", str(lib), "-s", *plan.to_add, "-a", agent, "-y", *scope])
    if plan.to_remove:
        cmds.append(["npx", "--yes", "skills", "remove", *plan.to_remove, "-a", agent, "-y", *scope])
    return cmds


def run(cmds: list[list[str]], project: Path, dry_run: bool = False, exec_=subprocess.run) -> int:
    for cmd in cmds:
        print("$", " ".join(cmd))
        if dry_run:
            continue
        rc = exec_(cmd, cwd=project).returncode
        if rc:
            return rc
    return 0
