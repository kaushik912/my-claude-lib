"""Skills: catalog = lib `skills/*/SKILL.md`; installed/added/removed via `npx skills`."""
import json
from pathlib import Path

from .base import Action, Ctx, Item, frontmatter

SKILLS_DIR = Path(".claude/skills")


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
        root = project / SKILLS_DIR
        return {p.parent.name for p in root.glob("*/SKILL.md")} if root.is_dir() else set()

    def add(self, names, ctx: Ctx) -> list[Action]:
        return [self._npx(ctx, ["add", str(ctx.lib), "-s", *names, "-a", ctx.agent, "-y"])]

    def remove(self, names, ctx: Ctx) -> list[Action]:
        return [self._npx(ctx, ["remove", *names, "-a", ctx.agent, "-y"])]

    @staticmethod
    def _npx(ctx: Ctx, args: list[str]) -> Action:
        cmd = ["npx", "--yes", "skills", *args, *(["-g"] if ctx.global_ else [])]
        return Action(" ".join(cmd), lambda: ctx.exec_(cmd, cwd=ctx.project).returncode)
