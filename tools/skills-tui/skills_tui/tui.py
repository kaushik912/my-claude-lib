"""Two questionary screens. All selection logic lives elsewhere; this only renders and returns."""
import questionary

from .catalog import Skill


def pick_profiles(profiles: dict[str, dict]) -> list[str]:
    if not profiles:
        return []
    choices = [questionary.Choice(n, value=n) for n in sorted(profiles)]
    return questionary.checkbox("Profiles to pre-tick (Enter to skip)", choices=choices).ask() or []


def pick_skills(catalog: list[Skill], installed: set[str], preticked: set[str]) -> set[str] | None:
    choices = []
    for origin in ("mine", "vendored"):
        group = [s for s in catalog if s.origin == origin]
        if not group:
            continue
        choices.append(questionary.Separator(f"── {origin} ──"))
        for s in group:
            mark = "[installed] " if s.name in installed else ""
            title = f"{s.name}  {mark}{s.description[:70]}"
            choices.append(questionary.Choice(title, value=s.name, checked=s.name in installed or s.name in preticked))
    picked = questionary.checkbox("Space = toggle, Enter = apply (unticking installed = remove)", choices=choices).ask()
    return None if picked is None else set(picked)
