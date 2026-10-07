from skills_tui.installed import installed_skills
from tests.conftest import write_skill


def test_given_installed_skills_when_scan_then_names(tmp_path):
    write_skill(tmp_path / ".claude/skills", "alpha")
    (tmp_path / ".claude/skills/notskill").mkdir()
    assert installed_skills(tmp_path) == {"alpha"}


def test_given_no_dir_when_scan_then_empty(tmp_path):
    assert installed_skills(tmp_path) == set()
