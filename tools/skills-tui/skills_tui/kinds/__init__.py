"""Registry. To add a kind: implement Kind (see base.py), or add a CopyKind line for a `.claude/<dir>/*.md` kind."""
from .base import Action, Ctx, Item, Kind
from .copy import CopyKind
from .skills import SkillsKind

KINDS: list[Kind] = [
    SkillsKind(),
    CopyKind("rules", "rules"),
    CopyKind("commands", "commands"),
    CopyKind("agents", "agents"),
]

__all__ = ["Action", "Ctx", "Item", "Kind", "KINDS"]
