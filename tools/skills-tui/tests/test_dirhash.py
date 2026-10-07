import json
import shutil
import subprocess
from pathlib import Path

import pytest

from skills_tui.cli import LIB
from skills_tui.dirhash import diff_files, tree_hash


def test_given_same_content_when_hash_then_equal_and_content_sensitive(tmp_path):
    for n in "ab":
        (tmp_path / n).mkdir()
        (tmp_path / n / "SKILL.md").write_text("x")
    assert tree_hash(tmp_path / "a") == tree_hash(tmp_path / "b")
    (tmp_path / "b" / "SKILL.md").write_text("y")
    assert tree_hash(tmp_path / "a") != tree_hash(tmp_path / "b")


def test_given_rename_when_hash_then_differs(tmp_path):
    (tmp_path / "a").mkdir(); (tmp_path / "b").mkdir()
    (tmp_path / "a" / "one.md").write_text("x")
    (tmp_path / "b" / "two.md").write_text("x")
    assert tree_hash(tmp_path / "a") != tree_hash(tmp_path / "b")


def test_given_dirs_when_diff_then_changed_extra_missing(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    (a / "sub").mkdir(parents=True); (b / "sub").mkdir(parents=True)
    (a / "same.md").write_text("1"); (b / "same.md").write_text("1")
    (a / "chg.md").write_text("1"); (b / "chg.md").write_text("2")
    (a / "sub/extra.md").write_text("1")
    (b / "missing.md").write_text("1")
    assert diff_files(a, b) == (["chg.md"], ["sub/extra.md"], ["missing.md"])


@pytest.mark.skipif(not shutil.which("npx"), reason="npx not installed")
def test_hash_matches_real_npx_skills_lock(tmp_path):
    """Guards the reverse-engineered algorithm: multi-file + nested + mixed-case names."""
    proj = tmp_path / "proj"
    proj.mkdir()
    skills = ["karpathy-guidelines", "mysql-query", "debug-live"]
    r = subprocess.run(["npx", "--yes", "skills", "add", str(LIB), "-s", *skills, "-a", "claude-code", "codex", "-y"],
                       cwd=proj, capture_output=True, text=True, timeout=120)
    if r.returncode or not (proj / "skills-lock.json").exists():
        pytest.skip(f"npx skills unavailable: {r.stderr[-200:]}")
    lock = json.loads((proj / "skills-lock.json").read_text())["skills"]
    for n in skills:
        assert tree_hash(proj / ".agents/skills" / n) == lock[n]["computedHash"], n
