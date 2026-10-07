"""Two questionary screens. All selection logic lives elsewhere; this only renders and returns."""
import questionary

from .kinds import Item


def pick_profiles(profiles: dict[str, dict]) -> list[str]:
    if not profiles:
        return []
    choices = [questionary.Choice(n, value=n) for n in sorted(profiles)]
    return questionary.checkbox("Profiles to pre-tick (Enter to skip)", choices=choices).ask() or []


def pick_items(catalog: list[Item], installed: set[str], preticked: set[str]) -> set[str] | None:
    choices = []
    groups = sorted({(i.kind, i.origin) for i in catalog}, key=lambda g: (g[0], g[1] != "mine"))
    for kind, origin in groups:
        choices.append(questionary.Separator(f"── {kind}: {origin} ──"))
        for i in (i for i in catalog if (i.kind, i.origin) == (kind, origin)):
            mark = "[installed] " if i.key in installed else ""
            title = f"{i.name}  {mark}{i.description[:70]}"
            choices.append(questionary.Choice(title, value=i.key, checked=i.key in installed or i.key in preticked))
    picked = questionary.checkbox("Space = toggle, Enter = apply (unticking installed = remove)", choices=choices).ask()
    return None if picked is None else set(picked)
