"""Profiles: named item sets, keyed by kind: {"skills": [...], "rules": [...], "extends": [...]}."""
import json
from pathlib import Path

from .catalog import ResolveError


class ProfileError(ResolveError):
    pass


def load_profiles(path: Path) -> dict[str, dict]:
    return json.loads(path.read_text()) if path.is_file() else {}


def resolve(name: str, profiles: dict[str, dict], known: set[str], _seen: tuple = ()) -> set[str]:
    """Returns `kind/name` keys. `known` = every catalog key."""
    if name in _seen:
        raise ProfileError(f"profile cycle: {' -> '.join((*_seen, name))}")
    if name not in profiles:
        raise ProfileError(f"unknown profile: {name}")
    prof = profiles[name]
    out: set[str] = set()
    for parent in prof.get("extends", []):
        out |= resolve(parent, profiles, known, (*_seen, name))
    own = {f"{kind}/{n}" for kind, names in prof.items() if kind != "extends" for n in names}
    unknown = own - known
    if unknown:
        raise ProfileError(f"profile {name!r} has unknown items: {', '.join(sorted(unknown))}")
    return out | own
