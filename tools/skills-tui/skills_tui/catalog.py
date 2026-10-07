"""Catalog = every `skills/<name>/SKILL.md` in the lib; vendored ones are listed in its skills-lock.json."""
import json
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    origin: str  # "mine" | "vendored"


def _frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    data = yaml.safe_load(parts[1])
    return data if isinstance(data, dict) else {}


def load_catalog(lib: Path) -> list[Skill]:
    lock = lib / "skills-lock.json"
    vendored = set(json.loads(lock.read_text()).get("skills", {})) if lock.is_file() else set()
    skills = []
    for md in sorted((lib / "skills").glob("*/SKILL.md")):
        meta = _frontmatter(md.read_text())
        name = md.parent.name
        desc = " ".join(str(meta.get("description", "")).split())
        skills.append(Skill(name, desc, "vendored" if name in vendored else "mine"))
    return skills
