# skills-tui

TUI to pick skills from this lib's curated catalog (`skills/` + vendored ones in `skills-lock.json`) and install them with `npx skills add <lib path>`. Project scope, Claude agent by default.

```
tools/skills-tui/install.sh      # venv + ~/.local/bin/skills-tui link
tools/skills-tui/uninstall.sh    # remove link + venv (never touches skills)
skills-tui [project]             # TUI: profiles -> kind menu (n/total) -> per-kind list; type to filter, installed first
skills-tui --doctor [project]       # health check of skills-lock.json (rare use); --yes = recommended fixes only, --dry-run
skills-tui --list                # catalog, * = installed in project
skills-tui --profile battletested --no-tui   # additive, no prompt
skills-tui --pick spec bruno --no-tui --yes
```

- Installed skills (`.claude/skills/*`) start ticked; unticking one removes it. Skills not in the catalog are never touched.
- Profiles: `profiles.json`, keyed by kind: `{"skills": [...], "rules": [...], "extends": [...]}`. Picking one pre-ticks its items.
- Add a kind (rules, commands, agents): for another `.claude/<dir>/*.md` kind add a `CopyKind(name, dir)` line to `KINDS`; otherwise write `skills_tui/kinds/<x>.py` implementing `Kind` (`catalog`, `installed`, `add`, `remove` -> `Action`s; copy or shell out), add it to `KINDS` in `kinds/__init__.py`. Core is untouched; see `tests/test_extension.py`. Items are `kind/name` keys; bare names work in `--pick` when unambiguous.
- Flags: `--agent`, `--global`, `--dry-run`, `--yes`.
- Modules: `kinds/` (extension seam; `skills` via npx; `rules`, `commands`, `agents` = `CopyKind`s copying `.claude/<dir>/*.md` as real files (project-only)), `catalog`, `profiles`, `plan` (pure) · `runner` · `tui`, `cli`.
- Tests: `.venv/bin/pip install -r requirements-dev.txt && .venv/bin/python -m pytest`.

## Doctor (`--doctor`, skills only)
Compares each `skills-lock.json` entry's project copy, lib source and `computedHash` (SHA-256 over sorted relpath+content; see `dirhash.py`). States: `outdated` (lib changed, rec. update), `modified` (project edited), `conflict`, `lock-stale`, `dangling` (dir missing), `orphan` (gone from lib, rec. delete), `dead-source` (lock path unresolvable), `untracked` (dir w/o lock entry), `foreign` (other source, report-only), `corrupt` (bad/unknown lock, report-only). Per issue: update / delete / keep. All fixes go through `npx skills add|remove`; the lock is never hand-edited. Copy kinds (rules/commands/agents) have no lock, so no doctor yet.
