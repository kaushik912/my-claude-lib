import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def write_skill(root: Path, name: str, desc: str = "d") -> None:
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: >-\n  {desc}\n  more\n---\nbody\n")


@pytest.fixture
def lib(tmp_path):
    root = tmp_path / "lib"
    for n in ("alpha", "beta", "gamma"):
        write_skill(root / "skills", n, f"{n} desc")
    (root / "skills-lock.json").write_text(json.dumps({"version": 1, "skills": {"gamma": {}}}))
    return root
