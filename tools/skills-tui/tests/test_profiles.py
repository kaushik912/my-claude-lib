import pytest

from skills_tui.profiles import ProfileError, load_profiles, resolve

KNOWN = {"a", "b", "c"}


def test_given_extends_when_resolve_then_union():
    p = {"base": {"skills": ["a"]}, "top": {"extends": ["base"], "skills": ["b"]}}
    assert resolve("top", p, KNOWN) == {"a", "b"}


def test_given_unknown_profile_when_resolve_then_error():
    with pytest.raises(ProfileError, match="unknown profile"):
        resolve("nope", {}, KNOWN)


def test_given_unknown_skill_when_resolve_then_error():
    with pytest.raises(ProfileError, match="zzz"):
        resolve("p", {"p": {"skills": ["zzz"]}}, KNOWN)


def test_given_cycle_when_resolve_then_error():
    p = {"x": {"extends": ["y"]}, "y": {"extends": ["x"]}}
    with pytest.raises(ProfileError, match="cycle"):
        resolve("x", p, KNOWN)


def test_given_missing_file_when_load_then_empty(tmp_path):
    assert load_profiles(tmp_path / "none.json") == {}


def test_shipped_profiles_only_reference_real_skills():
    from pathlib import Path

    from skills_tui.catalog import load_catalog
    from skills_tui.cli import LIB, TOOL_DIR

    names = {s.name for s in load_catalog(LIB)}
    profiles = load_profiles(TOOL_DIR / "profiles.json")
    for p in profiles:
        resolve(p, profiles, names)
