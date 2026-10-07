# skills-tui

TUI to pick skills from this lib's curated catalog (`skills/` + vendored ones in `skills-lock.json`) and install them with `npx skills add <lib path>`. Project scope, Claude agent by default.

```
tools/skills-tui/install.sh      # venv + ~/.local/bin/skills-tui link
tools/skills-tui/uninstall.sh    # remove link + venv (never touches skills)
skills-tui [project]             # TUI: pick profiles, then toggle skills
skills-tui --list                # catalog, * = installed in project
skills-tui --profile battletested --no-tui   # additive, no prompt
skills-tui --pick spec bruno --no-tui --yes
```

- Installed skills (`.claude/skills/*`) start ticked; unticking one removes it. Skills not in the catalog are never touched.
- Profiles: `profiles.json` (`skills`, optional `extends`). Picking one pre-ticks its skills.
- Flags: `--agent`, `--global`, `--dry-run`, `--yes`.
- Modules: `catalog`, `profiles`, `installed`, `plan` (pure) · `runner` (shells out) · `tui`, `cli`.
- Tests: `.venv/bin/pip install -r requirements-dev.txt && .venv/bin/python -m pytest`.
