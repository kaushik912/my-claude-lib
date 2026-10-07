"""Which skills a project already has (where `npx skills -a claude-code` puts them)."""
from pathlib import Path

SKILLS_DIR = Path(".claude/skills")


def installed_skills(project: Path, skills_dir: Path = SKILLS_DIR) -> set[str]:
    root = project / skills_dir
    return {p.parent.name for p in root.glob("*/SKILL.md")} if root.is_dir() else set()
