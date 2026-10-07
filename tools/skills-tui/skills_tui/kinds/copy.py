"""Copy kinds (rules, commands, agents): lib `.claude/<subdir>/*.md` -> project `.claude/<subdir>/`, real files only."""
import shutil
from pathlib import Path

from .base import Action, Ctx, Item, frontmatter


def _describe(text: str) -> str:
    desc = frontmatter(text).get("description")
    if desc:
        return " ".join(str(desc).split())
    return next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), "")


class CopyKind:
    def __init__(self, name: str, subdir: str):
        self.name = name
        self.dir = Path(".claude") / subdir

    def catalog(self, lib: Path) -> list[Item]:
        return [Item(self.name, md.stem, _describe(md.read_text()), "mine") for md in sorted((lib / self.dir).glob("*.md"))]

    def installed(self, project: Path) -> set[str]:
        root = project / self.dir
        return {md.stem for md in root.glob("*.md")} if root.is_dir() else set()

    def add(self, names, ctx: Ctx) -> list[Action]:
        self._project_only(ctx)
        return [Action(f"copy {self.dir / n}.md", lambda n=n: self._copy(n, ctx)) for n in names]

    def remove(self, names, ctx: Ctx) -> list[Action]:
        self._project_only(ctx)
        return [Action(f"rm {self.dir / n}.md", lambda n=n: self._rm(n, ctx)) for n in names]

    def _project_only(self, ctx: Ctx) -> None:
        if ctx.global_:
            raise ValueError(f"{self.name}: --global not supported (project-only)")

    def _copy(self, name: str, ctx: Ctx) -> int:
        dest = ctx.project / self.dir / f"{name}.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ctx.lib / self.dir / f"{name}.md", dest)  # real file, never a symlink
        return 0

    def _rm(self, name: str, ctx: Ctx) -> int:
        (ctx.project / self.dir / f"{name}.md").unlink(missing_ok=True)
        return 0
