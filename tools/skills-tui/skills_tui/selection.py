"""Pure helpers behind the drill-down TUI."""
from .kinds import Item


def order(items: list[Item], installed: set[str]) -> list[Item]:
    """Installed first, then mine before vendored, then by name."""
    return sorted(items, key=lambda i: (i.key not in installed, i.origin != "mine", i.name))


def kind_counts(catalog: list[Item], selected: set[str]) -> dict[str, tuple[int, int]]:
    """kind -> (ticked, total), in catalog order."""
    out: dict[str, tuple[int, int]] = {}
    for i in catalog:
        n, t = out.get(i.kind, (0, 0))
        out[i.kind] = (n + (i.key in selected), t + 1)
    return out


def merge(selected: set[str], kind_keys: set[str], picked: set[str]) -> set[str]:
    """Replace this kind's slice of the selection with `picked`; other kinds untouched."""
    return (selected - kind_keys) | (picked & kind_keys)
