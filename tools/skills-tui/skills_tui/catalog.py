"""Aggregates every kind's catalog / installed state into `kind/name` keys."""
from pathlib import Path

from .kinds import Item, Kind


class ResolveError(ValueError):
    pass


def load_catalog(lib: Path, kinds: list[Kind]) -> list[Item]:
    return [item for k in kinds for item in k.catalog(lib)]


def installed_keys(project: Path, kinds: list[Kind]) -> set[str]:
    return {f"{k.name}/{n}" for k in kinds for n in k.installed(project)}


def resolve_key(token: str, keys: set[str]) -> str:
    """Accept `kind/name` or a bare name that is unique across kinds."""
    if token in keys:
        return token
    matches = sorted(k for k in keys if k.split("/", 1)[1] == token)
    if len(matches) == 1:
        return matches[0]
    raise ResolveError(f"ambiguous: {token} ({', '.join(matches)})" if matches else f"unknown item: {token}")
