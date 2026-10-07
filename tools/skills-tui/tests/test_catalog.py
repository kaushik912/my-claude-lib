import pytest

from skills_tui.catalog import ResolveError, installed_keys, load_catalog, resolve_key
from skills_tui.kinds import KINDS
from tests.conftest import write_skill


def test_given_lib_when_load_then_lists_skills_with_origin(lib):
    cat = {i.key: i for i in load_catalog(lib, KINDS)}
    assert set(cat) == {"skills/alpha", "skills/beta", "skills/gamma"}
    assert cat["skills/alpha"].origin == "mine"
    assert cat["skills/gamma"].origin == "vendored"


def test_given_multiline_description_when_load_then_joined(lib):
    assert {i.name: i for i in load_catalog(lib, KINDS)}["alpha"].description == "alpha desc more"


def test_given_no_lock_when_load_then_all_mine(lib):
    (lib / "skills-lock.json").unlink()
    assert {i.origin for i in load_catalog(lib, KINDS)} == {"mine"}


def test_given_dir_without_skill_md_when_load_then_ignored(lib):
    (lib / "skills" / "junk").mkdir()
    assert "skills/junk" not in {i.key for i in load_catalog(lib, KINDS)}


def test_given_installed_skills_when_scan_then_keys(tmp_path):
    write_skill(tmp_path / ".claude/skills", "alpha")
    (tmp_path / ".claude/skills/notskill").mkdir()
    assert installed_keys(tmp_path, KINDS) == {"skills/alpha"}


def test_given_no_skills_dir_when_scan_then_empty(tmp_path):
    assert installed_keys(tmp_path, KINDS) == set()


def test_resolve_key_bare_qualified_unknown_and_ambiguous():
    keys = {"skills/a", "rules/a", "skills/b"}
    assert resolve_key("b", keys) == "skills/b"
    assert resolve_key("rules/a", keys) == "rules/a"
    with pytest.raises(ResolveError, match="ambiguous"):
        resolve_key("a", keys)
    with pytest.raises(ResolveError, match="unknown"):
        resolve_key("zzz", keys)


def test_given_agents_and_claude_dirs_when_scan_then_union_without_duplicates(tmp_path):
    write_skill(tmp_path / ".agents/skills", "alpha")
    (tmp_path / ".claude/skills").mkdir(parents=True)
    (tmp_path / ".claude/skills/alpha").symlink_to("../../.agents/skills/alpha")
    write_skill(tmp_path / ".claude/skills", "legacy")
    assert installed_keys(tmp_path, KINDS) == {"skills/alpha", "skills/legacy"}
