from skills_tui.catalog import load_catalog


def test_given_lib_when_load_then_lists_skills_with_origin(lib):
    cat = {s.name: s for s in load_catalog(lib)}
    assert set(cat) == {"alpha", "beta", "gamma"}
    assert cat["alpha"].origin == "mine"
    assert cat["gamma"].origin == "vendored"


def test_given_multiline_description_when_load_then_joined(lib):
    assert {s.name: s for s in load_catalog(lib)}["alpha"].description == "alpha desc more"


def test_given_no_lock_when_load_then_all_mine(lib):
    (lib / "skills-lock.json").unlink()
    assert {s.origin for s in load_catalog(lib)} == {"mine"}


def test_given_dir_without_skill_md_when_load_then_ignored(lib):
    (lib / "skills" / "junk").mkdir()
    assert "junk" not in {s.name for s in load_catalog(lib)}
