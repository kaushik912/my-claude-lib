"""Doctor orchestration: diagnose -> decide -> apply through the normal plan/runner (so only `npx skills` mutates)."""
from pathlib import Path

from . import tui
from .doctor import DELETE, UPDATE, diagnose
from .kinds import Ctx
from .kinds.skills import SkillsKind
from .plan import Plan
from .runner import build_actions, run


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
    if not plan:
        print("nothing to apply")
        return 0
    print(f"update: {', '.join(k.split('/', 1)[1] for k in plan.to_add) or '-'}\ndelete: {', '.join(k.split('/', 1)[1] for k in plan.to_remove) or '-'}")
    if not (yes or dry_run) and not confirm():
        return 1
    return run(build_actions(plan, [SkillsKind()], ctx), dry_run)
