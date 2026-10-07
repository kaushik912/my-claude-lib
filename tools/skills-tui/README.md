# skills-tui

TUI to pick skills from this lib's curated catalog (`skills/` + vendored ones in `skills-lock.json`) and install them with `npx skills add <lib path>`. Project scope, Claude agent by default.

```
tools/skills-tui/install.sh      # venv + ~/.local/bin/skills-tui link
tools/skills-tui/uninstall.sh    # remove link + venv (never touches skills)
skills-tui [project]             # TUI: profiles -> kind menu (n/total) -> per-kind list; type to filter, installed first
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
