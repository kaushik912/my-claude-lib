"""Registry. To add a kind (rules, commands, ...): write kinds/<x>.py implementing Kind, add it below."""
from .base import Action, Ctx, Item, Kind
from .skills import SkillsKind

KINDS: list[Kind] = [SkillsKind()]

__all__ = ["Action", "Ctx", "Item", "Kind", "KINDS"]
