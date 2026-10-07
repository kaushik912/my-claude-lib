"""Rules: catalog = lib `.claude/rules/*.md`; add = copy into project `.claude/rules/`, remove = delete the copy."""
import shutil
from pathlib import Path

from .base import Action, Ctx, Item

RULES_DIR = Path(".claude/rules")


def _describe(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


class RulesKind:
    name = "rules"

    def catalog(self, lib: Path) -> list[Item]:
        return [Item(self.name, md.stem, _describe(md.read_text()), "mine") for md in sorted((lib / RULES_DIR).glob("*.md"))]

    def installed(self, project: Path) -> set[str]:
        root = project / RULES_DIR
        return {md.stem for md in root.glob("*.md")} if root.is_dir() else set()

    def add(self, names, ctx: Ctx) -> list[Action]:
        self._project_only(ctx)
        return [Action(f"copy .claude/rules/{n}.md", lambda n=n: self._copy(n, ctx)) for n in names]

    def remove(self, names, ctx: Ctx) -> list[Action]:
        self._project_only(ctx)
        return [Action(f"rm .claude/rules/{n}.md", lambda n=n: self._rm(n, ctx)) for n in names]

    @staticmethod
    def _project_only(ctx: Ctx) -> None:
        if ctx.global_:
            raise ValueError("rules: --global not supported (project-only)")

    @staticmethod
    def _copy(name: str, ctx: Ctx) -> int:
        dest = ctx.project / RULES_DIR / f"{name}.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ctx.lib / RULES_DIR / f"{name}.md", dest)  # real file, never a symlink
        return 0

    @staticmethod
    def _rm(name: str, ctx: Ctx) -> int:
        (ctx.project / RULES_DIR / f"{name}.md").unlink(missing_ok=True)
        return 0
