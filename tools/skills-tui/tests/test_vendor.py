import json
from pathlib import Path

import pytest

from skills_tui import marketplace
from skills_tui.cli import LIB
from skills_tui.dirhash import tree_hash
from skills_tui.vendor import (CHANGED, NEW, PROTECTED, UNCHANGED, VendorError, classify, parse_vendors, risky_files,
                               write_lib_lock)
from tests.conftest import write_skill


def one(text):
    (v,) = parse_vendors(text)
    return v


def test_given_users_example_when_parse_then_source_skill_and_ignored_flag():
    v = one("npx skills add https://github.com/doraemonkeys/claude-code-debug-mode --skill debug-mode -g")
    assert v.source == "https://github.com/doraemonkeys/claude-code-debug-mode"
    assert v.skills == ("debug-mode",) and v.ignored == ("-g",) and v.bundle is None


def test_given_multi_skills_flags_comment_when_parse_then_all_captured():
    v = one("npx --yes skills add owner/repo -s a b -a claude-code cursor -y --copy  # bundle=my-bundle")
    assert v.skills == ("a", "b") and v.bundle == "my-bundle"
    assert v.ignored == ("-a", "claude-code", "cursor", "-y", "--copy")


def test_given_comments_and_blanks_when_parse_then_skipped_and_linenos_kept():
    text = "# header\n\nnpx skills add o/r -s a\n   # indented comment\nnpx skills add o/r2 -s b\n"
    assert [(v.lineno, v.source) for v in parse_vendors(text)] == [(3, "o/r"), (5, "o/r2")]


def test_given_hash_inside_url_when_parse_then_not_a_comment():
    assert one("npx skills add https://github.com/o/r#main -s a").source == "https://github.com/o/r#main"


@pytest.mark.parametrize("line,msg", [
    ("rm -rf /", "only"),
    ("npx other add o/r -s a", "only"),
    ("npx skills add o/r -s a; rm", "invalid skill name"),
    ("npx skills add o/r -s a; rm -rf /", "unsupported flag"),
    ("npx skills add o/r -s 'a b' $(x)", "invalid skill name"),
    ("npx skills add o/r", "missing --skill"),
    ("npx skills add -s a", "missing source"),
    ("npx skills add o/r -s '*'", "not allowed"),
    ("npx skills add o/r -s a --weird", "unsupported flag"),
    ("npx skills add o/r other -s a", "unexpected"),
    ("npx skills add 'o/r -s a", "unparseable"),
])
def test_given_bad_line_when_parse_then_rejected_with_lineno(line, msg):
    with pytest.raises(VendorError, match=rf"line 2: .*{msg}"):
        parse_vendors("# ok\n" + line)


# ---- classify ----

def incoming(tmp_path, name="x", text="up"):
    d = tmp_path / "incoming" / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(text)
    return d, {"source": "o/r", "computedHash": tree_hash(d)}


def test_given_not_in_lib_when_classify_then_new_with_risky_scripts(lib, tmp_path):
    d, e = incoming(tmp_path)
    (d / "run.sh").write_text("#!/bin/sh")
    c = classify("x", d, e, lib, {})
    assert c.status == NEW and c.risky == ("run.sh",) and "SKILL.md" in c.added


def test_given_same_content_when_classify_then_unchanged(lib, tmp_path):
    d, e = incoming(tmp_path, "gamma", "same")
    (lib / "skills/gamma/SKILL.md").write_text("same")
    assert classify("gamma", d, e, lib, {"gamma": {"source": "o/r"}}).status == UNCHANGED


def test_given_upstream_differs_when_classify_then_changed_with_file_lists(lib, tmp_path):
    d, e = incoming(tmp_path, "gamma", "new")
    (d / "extra.py").write_text("x")
    (lib / "skills/gamma/old.md").write_text("old")
    c = classify("gamma", d, e, lib, {"gamma": {"source": "o/r"}})
    assert c.status == CHANGED
    assert c.changed == ("SKILL.md",) and c.added == ("extra.py",) and c.removed == ("old.md",)
    assert c.risky == ("extra.py",)  # only incoming files are flagged


def test_given_own_skill_with_same_name_when_classify_then_protected(lib, tmp_path):
    d, e = incoming(tmp_path, "alpha")
    c = classify("alpha", d, e, lib, {"gamma": {"source": "o/r"}})
    assert c.status == PROTECTED and "your own" in c.detail


def test_given_other_vendor_owns_name_when_classify_then_protected(lib, tmp_path):
    d, e = incoming(tmp_path, "gamma")
    assert classify("gamma", d, e, lib, {"gamma": {"source": "someone/else"}}).status == PROTECTED


def test_given_executable_without_script_suffix_when_risky_then_flagged(tmp_path):
    (tmp_path / "bin").write_text("x")
    (tmp_path / "bin").chmod(0o755)
    (tmp_path / "doc.md").write_text("x")
    assert risky_files(tmp_path) == ("bin",)


# ---- format guards: merges must give minimal diffs ----

def test_real_lock_round_trips_through_writer(tmp_path):
    (tmp_path / "skills-lock.json").write_text((LIB / "skills-lock.json").read_text())
    skills = json.loads((LIB / "skills-lock.json").read_text())["skills"]
    write_lib_lock(tmp_path, dict(reversed(list(skills.items()))))
    assert (tmp_path / "skills-lock.json").read_text() == (LIB / "skills-lock.json").read_text()


def test_real_marketplace_round_trips(tmp_path):
    (tmp_path / ".claude-plugin").mkdir()
    (tmp_path / ".claude-plugin/marketplace.json").write_text((LIB / ".claude-plugin/marketplace.json").read_text())
    marketplace.save(tmp_path, marketplace.load(tmp_path))
    assert (tmp_path / ".claude-plugin/marketplace.json").read_text() == (LIB / ".claude-plugin/marketplace.json").read_text()


def test_given_bundle_when_add_then_appended_or_created():
    data = {"plugins": [{"name": "a", "skills": ["./skills/x"]}]}
    marketplace.add_to_bundle(data, "a", ["y", "x"])
    marketplace.add_to_bundle(data, "new", ["z"], description="d")
    assert data["plugins"][0]["skills"] == ["./skills/x", "./skills/y"]
    assert data["plugins"][1] == {"name": "new", "description": "d", "source": "./", "strict": False, "skills": ["./skills/z"]}
    assert marketplace.bundled_skills(data) == {"x", "y", "z"}


def test_shipped_vendors_file_parses_and_matches_lock():
    lines = parse_vendors((LIB / "vendors.txt").read_text())
    lock = json.loads((LIB / "skills-lock.json").read_text())["skills"]
    assert {s for v in lines for s in v.skills} == set(lock)
