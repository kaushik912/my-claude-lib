"""Registry. To add a kind (rules, commands, ...): write kinds/<x>.py implementing Kind, add it below."""
from .base import Action, Ctx, Item, Kind
from .rules import RulesKind
from .skills import SkillsKind

KINDS: list[Kind] = [SkillsKind(), RulesKind()]

__all__ = ["Action", "Ctx", "Item", "Kind", "KINDS"]
