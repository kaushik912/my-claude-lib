"""Skills: catalog = lib `skills/*/SKILL.md`; installed/added/removed via `npx skills`."""
import json
from pathlib import Path

from .base import Action, Ctx, Item, frontmatter

CANON_DIR = Path(".agents/skills")  # real files
CLAUDE_DIR = Path(".claude/skills")  # symlinks into CANON_DIR (real dirs only in legacy installs)


class SkillsKind:
    name = "skills"

    def catalog(self, lib: Path) -> list[Item]:
        lock = lib / "skills-lock.json"
        vendored = set(json.loads(lock.read_text()).get("skills", {})) if lock.is_file() else set()
        items = []
        for md in sorted((lib / "skills").glob("*/SKILL.md")):
            desc = " ".join(str(frontmatter(md.read_text()).get("description", "")).split())
            name = md.parent.name
            items.append(Item(self.name, name, desc, "vendored" if name in vendored else "mine"))
        return items

    def installed(self, project: Path) -> set[str]:
        names: set[str] = set()
        for base in (CANON_DIR, CLAUDE_DIR):
            root = project / base
            if root.is_dir():
                names |= {p.parent.name for p in root.glob("*/SKILL.md")}
        return names

    def add(self, names, ctx: Ctx) -> list[Action]:
        return [self._npx(ctx, ["add", str(ctx.lib), "-s", *names, "-a", *ctx.agents, "-y"])]

    def remove(self, names, ctx: Ctx) -> list[Action]:
        return [self._npx(ctx, ["remove", *names, "-a", *ctx.agents, "-y"])]

    @staticmethod
    def _npx(ctx: Ctx, args: list[str]) -> Action:
        cmd = ["npx", "--yes", "skills", *args, *(["-g"] if ctx.global_ else [])]
        return Action(" ".join(cmd), lambda: ctx.exec_(cmd, cwd=ctx.project).returncode)
