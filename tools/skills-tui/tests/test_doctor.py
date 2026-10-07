import json
import os
from pathlib import Path

from skills_tui.dirhash import tree_hash
from skills_tui.doctor import (CONFLICT, CORRUPT, DANGLING, DEAD_SOURCE, FOREIGN, LEGACY, LOCK_STALE, MODIFIED, ORPHAN,
                               OUTDATED, UNLINKED, UNTRACKED, diagnose)
from tests.conftest import write_skill


def installed(project: Path, lib: Path, name: str, *, lock=True, legacy=False):
    """Simulate `npx skills add -a claude-code codex`: real files in .agents/skills, symlink in .claude/skills.
    legacy=True: old layout, real copy in .claude/skills only."""
    src = lib / "skills" / name
    dest = project / (".claude/skills" if legacy else ".agents/skills") / name
    dest.mkdir(parents=True)
    for f in src.rglob("*"):
        if f.is_file():
            (dest / f.relative_to(src)).parent.mkdir(parents=True, exist_ok=True)
            (dest / f.relative_to(src)).write_bytes(f.read_bytes())
    if not legacy:
        link = project / ".claude/skills" / name
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(Path("../../.agents/skills") / name)
    if lock:
        write_lock(project, {name: entry(project, lib, name)})


def entry(project, lib, name, **over):
    e = {"source": os.path.relpath(lib, project), "sourceType": "local", "computedHash": tree_hash(lib / "skills" / name)}
    return {**e, **over}


def write_lock(project: Path, skills: dict, version=1):
    p = project / "skills-lock.json"
    cur = json.loads(p.read_text())["skills"] if p.exists() else {}
    p.write_text(json.dumps({"version": version, "skills": {**cur, **skills}}))


def states(project, lib):
    return {i.name: i.state for i in diagnose(project, lib)}


def test_given_healthy_when_diagnose_then_no_issues(lib, tmp_path):
    installed(tmp_path, lib, "alpha")
    assert diagnose(tmp_path, lib) == []


def test_given_lib_changed_when_diagnose_then_outdated_recommend_update(lib, tmp_path):
    installed(tmp_path, lib, "alpha")
    (lib / "skills/alpha/SKILL.md").write_text("new")
    (issue,) = diagnose(tmp_path, lib)
    assert issue.state == OUTDATED and issue.recommended == "update" and "SKILL.md" in issue.detail


def test_given_project_edited_when_diagnose_then_modified_no_recommendation(lib, tmp_path):
    installed(tmp_path, lib, "alpha")
    (tmp_path / ".claude/skills/alpha/SKILL.md").write_text("mine")
    (issue,) = diagnose(tmp_path, lib)
    assert issue.state == MODIFIED and issue.recommended is None and issue.options == ("update", "keep")


def test_given_both_changed_when_diagnose_then_conflict(lib, tmp_path):
    installed(tmp_path, lib, "alpha")
    (lib / "skills/alpha/SKILL.md").write_text("lib")
    (tmp_path / ".claude/skills/alpha/SKILL.md").write_text("proj")
    assert states(tmp_path, lib) == {"alpha": CONFLICT}


def test_given_project_equals_lib_but_lock_old_when_diagnose_then_lock_stale(lib, tmp_path):
    installed(tmp_path, lib, "alpha")
    write_lock(tmp_path, {"alpha": entry(tmp_path, lib, "alpha", computedHash="0" * 64)})
    assert states(tmp_path, lib) == {"alpha": LOCK_STALE}


def test_given_dir_deleted_when_diagnose_then_dangling(lib, tmp_path):
    installed(tmp_path, lib, "alpha")
    import shutil
    shutil.rmtree(tmp_path / ".agents/skills/alpha")  # leaves a dangling .claude symlink
    assert states(tmp_path, lib) == {"alpha": DANGLING}


def test_given_skill_removed_from_lib_when_diagnose_then_orphan_recommend_delete(lib, tmp_path):
    installed(tmp_path, lib, "alpha")
    import shutil
    shutil.rmtree(lib / "skills/alpha")
    (issue,) = diagnose(tmp_path, lib)
    assert issue.state == ORPHAN and issue.recommended == "delete"


def test_given_source_path_gone_when_diagnose_then_dead_source_offers_relink(lib, tmp_path):
    installed(tmp_path, lib, "alpha")
    write_lock(tmp_path, {"alpha": entry(tmp_path, lib, "alpha", source="../nowhere/lib")})
    (issue,) = diagnose(tmp_path, lib)
    assert issue.state == DEAD_SOURCE and issue.options == ("update", "keep")


def test_given_other_sources_when_diagnose_then_foreign_report_only(lib, tmp_path):
    other = tmp_path / "other"
    write_skill(other / "skills", "alpha")
    proj = tmp_path / "proj"
    proj.mkdir()
    write_lock(proj, {
        "alpha": entry(proj, other, "alpha"),                              # local, different lib
        "gamma": {"source": "owner/repo", "sourceType": "github", "computedHash": "x"},
    })
    issues = {i.name: i for i in diagnose(proj, lib)}
    assert {n: i.state for n, i in issues.items()} == {"alpha": FOREIGN, "gamma": FOREIGN}
    assert all(i.options == () for i in issues.values())


def test_given_dir_without_lock_entry_when_diagnose_then_untracked(lib, tmp_path):
    installed(tmp_path, lib, "alpha", lock=False)
    assert states(tmp_path, lib) == {"alpha": UNTRACKED}


def test_given_unknown_or_symlinked_dirs_when_diagnose_then_ignored(lib, tmp_path):
    (tmp_path / ".claude/skills/third-party").mkdir(parents=True)
    (tmp_path / ".claude/skills/third-party/SKILL.md").write_text("x")
    (tmp_path / ".claude/skills/beta").symlink_to(lib / "skills/beta")  # my-pick style link
    assert diagnose(tmp_path, lib) == []


def test_given_bad_lock_when_diagnose_then_single_corrupt_issue(lib, tmp_path):
    (tmp_path / "skills-lock.json").write_text("{not json")
    assert states(tmp_path, lib) == {"skills-lock.json": CORRUPT}
    (tmp_path / "skills-lock.json").write_text('{"version": 99, "skills": {}}')
    assert states(tmp_path, lib) == {"skills-lock.json": CORRUPT}


def test_given_no_lock_and_no_dirs_when_diagnose_then_healthy(lib, tmp_path):
    assert diagnose(tmp_path, lib) == []


# ---- layout: real files in .agents/skills, symlink in .claude/skills ----

def test_given_legacy_real_copy_in_claude_only_when_diagnose_then_legacy_recommend_migrate(lib, tmp_path):
    installed(tmp_path, lib, "alpha", legacy=True)
    (issue,) = diagnose(tmp_path, lib)
    assert issue.state == LEGACY and issue.recommended == "update"


def test_given_claude_link_missing_when_diagnose_then_unlinked_recommend_relink(lib, tmp_path):
    installed(tmp_path, lib, "alpha")
    (tmp_path / ".claude/skills/alpha").unlink()
    (issue,) = diagnose(tmp_path, lib)
    assert issue.state == UNLINKED and "missing" in issue.detail and issue.recommended == "update"


def test_given_claude_real_dir_instead_of_link_when_diagnose_then_unlinked(lib, tmp_path):
    installed(tmp_path, lib, "alpha")
    (tmp_path / ".claude/skills/alpha").unlink()
    write_skill(tmp_path / ".claude/skills", "alpha")
    (issue,) = diagnose(tmp_path, lib)
    assert issue.state == UNLINKED and "not a symlink" in issue.detail


def test_given_claude_link_points_elsewhere_when_diagnose_then_unlinked(lib, tmp_path):
    installed(tmp_path, lib, "alpha")
    (tmp_path / ".claude/skills/alpha").unlink()
    (tmp_path / ".claude/skills/alpha").symlink_to(lib / "skills/beta")
    assert states(tmp_path, lib) == {"alpha": UNLINKED}


def test_given_content_changed_in_legacy_layout_when_diagnose_then_content_state_wins(lib, tmp_path):
    installed(tmp_path, lib, "alpha", legacy=True)
    (lib / "skills/alpha/SKILL.md").write_text("new")
    assert states(tmp_path, lib) == {"alpha": OUTDATED}


def test_given_untracked_in_agents_dir_when_diagnose_then_reported_once_ignoring_claude_link(lib, tmp_path):
    installed(tmp_path, lib, "alpha", lock=False)
    assert [i.name for i in diagnose(tmp_path, lib)] == ["alpha"]
