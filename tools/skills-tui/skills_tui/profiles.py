"""Profiles: named skill sets. `extends` pulls in other profiles."""
import json
from pathlib import Path


class ProfileError(ValueError):
    pass


def load_profiles(path: Path) -> dict[str, dict]:
    return json.loads(path.read_text()) if path.is_file() else {}


def resolve(name: str, profiles: dict[str, dict], known: set[str], _seen: tuple = ()) -> set[str]:
    if name in _seen:
        raise ProfileError(f"profile cycle: {' -> '.join((*_seen, name))}")
    if name not in profiles:
        raise ProfileError(f"unknown profile: {name}")
    prof = profiles[name]
    out: set[str] = set()
    for parent in prof.get("extends", []):
        out |= resolve(parent, profiles, known, (*_seen, name))
    unknown = set(prof.get("skills", [])) - known
    if unknown:
        raise ProfileError(f"profile {name!r} has unknown skills: {', '.join(sorted(unknown))}")
    return out | set(prof.get("skills", []))
