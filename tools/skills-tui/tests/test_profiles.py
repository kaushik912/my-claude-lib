import pytest

from skills_tui.profiles import ProfileError, load_profiles, resolve

KNOWN = {"skills/a", "skills/b", "rules/c"}


def test_given_extends_when_resolve_then_union_of_keys():
    p = {"base": {"skills": ["a"]}, "top": {"extends": ["base"], "skills": ["b"], "rules": ["c"]}}
    assert resolve("top", p, KNOWN) == {"skills/a", "skills/b", "rules/c"}


def test_given_unknown_profile_when_resolve_then_error():
    with pytest.raises(ProfileError, match="unknown profile"):
        resolve("nope", {}, KNOWN)


def test_given_unknown_item_when_resolve_then_error():
    with pytest.raises(ProfileError, match="skills/zzz"):
        resolve("p", {"p": {"skills": ["zzz"]}}, KNOWN)


def test_given_cycle_when_resolve_then_error():
    p = {"x": {"extends": ["y"]}, "y": {"extends": ["x"]}}
    with pytest.raises(ProfileError, match="cycle"):
        resolve("x", p, KNOWN)


def test_given_missing_file_when_load_then_empty(tmp_path):
    assert load_profiles(tmp_path / "none.json") == {}


def test_shipped_profiles_only_reference_real_items():
    from skills_tui.catalog import load_catalog
    from skills_tui.cli import LIB, TOOL_DIR
    from skills_tui.kinds import KINDS

    names = {i.key for i in load_catalog(LIB, KINDS)}
    profiles = load_profiles(TOOL_DIR / "profiles.json")
    for p in profiles:
        resolve(p, profiles, names)
