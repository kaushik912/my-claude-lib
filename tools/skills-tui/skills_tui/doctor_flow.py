"""Doctor orchestration: diagnose -> decide -> apply. npx-side fixes go through plan/runner (only `npx skills`
mutates the project); `push` copies project edits into the lib (see pushback.py)."""
from pathlib import Path

from . import tui
from .doctor import DELETE, PUSH, UPDATE, diagnose
from .kinds import Ctx
from .kinds.skills import SkillsKind
from .plan import Plan
from .pushback import PushError, apply_push, plan_push
from .runner import build_actions, run


def _names(keys) -> str:
    return ", ".join(k.split("/", 1)[1] for k in keys) or "-"


def run_doctor(project: Path, lib: Path, ctx: Ctx, *, yes: bool = False, dry_run: bool = False,
               choose=tui.doctor_choose, confirm=lambda: input("Apply? [y/N] ").strip().lower() == "y") -> int:
    issues = diagnose(project, lib)
    if not issues:
        print("healthy: nothing to fix")
        return 0
    for i in issues:
        print(f"{i.state:12} {i.name}: {i.detail}")
    actionable = [i for i in issues if i.options]
    if not actionable:
        return 0
    if yes:
        decisions = {i.name: i.recommended for i in actionable if i.recommended}
    else:
        decisions = choose(actionable)
        if decisions is None:
            return 1
    plan = Plan(
        to_add=tuple(f"skills/{n}" for n, d in sorted(decisions.items()) if d == UPDATE),
        to_remove=tuple(f"skills/{n}" for n, d in sorted(decisions.items()) if d == DELETE),
    )
    rc, pushes = 0, []
    for n in sorted(n for n, d in decisions.items() if d == PUSH):
        try:
            pushes.append(plan_push(project, lib, n))
        except PushError as e:
            print(f"error: {e}")
            rc = 1
    if not plan and not pushes:
        print("nothing to apply")
        return rc
    print(f"update: {_names(plan.to_add)}\ndelete: {_names(plan.to_remove)}\npush to lib: {', '.join(p.name for p in pushes) or '-'}")
    for p in pushes:
        print(f"  {p.name}:")
        print("\n".join(p.lines()))
    if not (yes or dry_run) and not confirm():
        return 1
    if not dry_run:
        for p in pushes:
            try:
                apply_push(p)
            except PushError as e:
                print(f"error: {e}")
                rc = 1
        if pushes:
            print("pushed; review with `git diff` in the lib (nothing committed). "
                  "Run --doctor again: the lock will show lock-stale -> update refreshes it.")
    return run(build_actions(plan, [SkillsKind()], ctx), dry_run) or rc
