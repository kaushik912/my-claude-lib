"""Turns a Plan into Actions (per kind) and executes them."""
from .kinds import Action, Ctx, Kind
from .plan import Plan


def build_actions(plan: Plan, kinds: list[Kind], ctx: Ctx) -> list[Action]:
    actions = []
    for kind in kinds:
        prefix = f"{kind.name}/"
        add = tuple(k[len(prefix):] for k in plan.to_add if k.startswith(prefix))
        rem = tuple(k[len(prefix):] for k in plan.to_remove if k.startswith(prefix))
        if add:
            actions += kind.add(add, ctx)
        if rem:
            actions += kind.remove(rem, ctx)
    return actions


def run(actions: list[Action], dry_run: bool = False) -> int:
    for a in actions:
        print("$", a.label)
        if dry_run:
            continue
        rc = a.run()
        if rc:
            return rc
    return 0
