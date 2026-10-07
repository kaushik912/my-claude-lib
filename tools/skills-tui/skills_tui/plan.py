"""Pure diff: what to add / remove so the project matches the selection."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    to_add: tuple[str, ...]
    to_remove: tuple[str, ...]

    def __bool__(self) -> bool:
        return bool(self.to_add or self.to_remove)


def make_plan(selected: set[str], installed: set[str], catalog: set[str]) -> Plan:
    """Only catalog skills are managed; installed skills from elsewhere are left alone."""
    selected = selected & catalog
    return Plan(
        to_add=tuple(sorted(selected - installed)),
        to_remove=tuple(sorted((installed & catalog) - selected)),
    )
