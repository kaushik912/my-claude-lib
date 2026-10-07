"""Questionary screens: profiles -> kind menu -> per-kind checkbox (type to filter). Logic lives in selection.py."""
import questionary

from .doctor import DELETE, KEEP, UPDATE, Issue
from .kinds import Item
from .selection import kind_counts, merge, order

APPLY, CANCEL = "__apply__", "__cancel__"


def pick_profiles(profiles: dict[str, dict]) -> list[str]:
    if not profiles:
        return []
    choices = [questionary.Choice(n, value=n) for n in sorted(profiles)]
    return questionary.checkbox("Profiles to pre-tick (Enter to skip)", choices=choices).ask() or []


def _menu(counts: dict[str, tuple[int, int]], default: str | None) -> str | None:
    choices = [questionary.Choice(f"{k}  ({n}/{t})", value=k) for k, (n, t) in counts.items()]
    choices += [questionary.Choice("✔ Apply", value=APPLY), questionary.Choice("✖ Cancel", value=CANCEL)]
    return questionary.select("Pick a kind (n/total ticked)", choices=choices, default=default).ask()


def _kind_screen(kind: str, items: list[Item], installed: set[str], selected: set[str]) -> set[str] | None:
    choices = []
    for i in items:
        tag = ("[installed] " if i.key in installed else "") + ("(vendored) " if i.origin == "vendored" else "")
        choices.append(questionary.Choice(f"{i.name}  {tag}{i.description[:60]}", value=i.key, checked=i.key in selected))
    picked = questionary.checkbox(
        f"{kind}: Space = toggle, type to filter, Enter = back", choices=choices, use_search_filter=True, use_jk_keys=False
    ).ask()
    return None if picked is None else set(picked)


def pick_items(catalog: list[Item], installed: set[str], preticked: set[str]) -> set[str] | None:
    selected = set(installed) | set(preticked)
    default = None
    while True:
        counts = kind_counts(catalog, selected)
        choice = _menu(counts, default or next(iter(counts), None))
        if choice in (None, CANCEL):
            return None
        if choice == APPLY:
            return selected
        default = choice
        items = order([i for i in catalog if i.kind == choice], installed)
        picked = _kind_screen(choice, items, installed, selected)
        if picked is not None:
            selected = merge(selected, {i.key for i in items}, picked)


UPDATE_LABELS = {
    "outdated": "update from lib", "modified": "revert to lib", "conflict": "overwrite with lib",
    "lock-stale": "refresh lock", "dangling": "restore from lib", "untracked": "adopt (reinstall from lib)",
    "dead-source": "re-link to this lib",
}


def _label(issue: Issue, option: str) -> str:
    if option == UPDATE:
        return UPDATE_LABELS.get(issue.state, "update")
    return {DELETE: "delete (npx skills remove)", KEEP: "keep as is"}[option]


def doctor_choose(issues: list[Issue]) -> dict[str, str] | None:
    """Returns name -> update|delete|keep, or None if cancelled."""
    decisions: dict[str, str] = {}
    recommended = [i for i in issues if i.recommended]
    if recommended:
        mode = questionary.select(
            f"{len(recommended)} issue(s) have a clear fix",
            choices=[
                questionary.Choice("Apply recommended, review the rest", "rec"),
                questionary.Choice("Review each one", "each"),
                questionary.Choice("Cancel", "cancel"),
            ],
        ).ask()
        if mode in (None, "cancel"):
            return None
        if mode == "rec":
            decisions = {i.name: i.recommended for i in recommended}
    for i in issues:
        if i.name in decisions:
            continue
        choices = [questionary.Choice(_label(i, o), o) for o in i.options]
        ans = questionary.select(f"{i.name} [{i.state}] {i.detail}", choices=choices, default=KEEP).ask()
        if ans is None:
            return None
        decisions[i.name] = ans
    return decisions
