# skills-tui

TUI to pick skills from this lib's curated catalog (`skills/` + vendored ones in `skills-lock.json`) and install them with `npx skills add <lib path>`. Project scope. Skills use the open-source layout: real files in `.agents/skills/<name>`, symlinks in `.claude/skills/<name>` (always `-a claude-code codex`; no other agents).

```
tools/skills-tui/install.sh      # venv + ~/.local/bin/skills-tui link
tools/skills-tui/uninstall.sh    # remove link + venv (never touches skills)
skills-tui [project]             # TUI: profiles -> kind menu (n/total) -> per-kind list; type to filter, installed first
skills-tui --doctor [project]       # health check of skills-lock.json (rare use); --yes = recommended fixes only, --dry-run
skills-tui --vendor [--dry-run|--yes]  # refresh vendored skills in the LIB from ../../vendors.txt (see below)
skills-tui --list                # catalog, * = installed in project
skills-tui --profile battletested --no-tui   # additive, no prompt
skills-tui --pick spec bruno --no-tui --yes
```

- Installed skills (`.claude/skills/*`) start ticked; unticking one removes it. Skills not in the catalog are never touched.
- Profiles: `profiles.json`, keyed by kind: `{"skills": [...], "rules": [...], "extends": [...]}`. Picking one pre-ticks its items.
- Add a kind (rules, commands, agents): for another `.claude/<dir>/*.md` kind add a `CopyKind(name, dir)` line to `KINDS`; otherwise write `skills_tui/kinds/<x>.py` implementing `Kind` (`catalog`, `installed`, `add`, `remove` -> `Action`s; copy or shell out), add it to `KINDS` in `kinds/__init__.py`. Core is untouched; see `tests/test_extension.py`. Items are `kind/name` keys; bare names work in `--pick` when unambiguous.
- Flags: `--global` (skills only), `--dry-run`, `--yes`.
- Modules: `kinds/` (extension seam; `skills` via npx; `rules`, `commands`, `agents` = `CopyKind`s copying `.claude/<dir>/*.md` as real files (project-only)), `catalog`, `profiles`, `plan` (pure) · `runner` · `tui`, `cli`.
- Tests: `.venv/bin/pip install -r requirements-dev.txt && .venv/bin/python -m pytest`.

## Doctor (`--doctor`, skills only)
Compares each `skills-lock.json` entry's project copy, lib source and `computedHash` (SHA-256 over sorted relpath+content; see `dirhash.py`). States: `legacy-layout` (real copy only in `.claude/skills`; update migrates it), `not-linked` (`.claude/skills/<n>` missing or not a symlink to `.agents/skills/<n>`; update re-links), `outdated` (lib changed, rec. update), `modified` (project edited), `conflict`, `lock-stale`, `dangling` (dir missing), `orphan` (gone from lib, rec. delete), `dead-source` (lock path unresolvable), `untracked` (dir w/o lock entry), `foreign` (other source, report-only), `corrupt` (bad/unknown lock, report-only). Per issue: update / delete / keep. All fixes go through `npx skills add|remove`; the lock is never hand-edited. Copy kinds (rules/commands/agents) have no lock, so no doctor yet.

## Vendor (`--vendor`, lib-side)
`vendors.txt` (lib root): one `npx skills add <source> --skill <names>` per line, `#` comments, trailing `# bundle=<name>` picks the marketplace bundle. Each line runs in a temp sandbox project (so `-g/-a/-y` are ignored and `~/.claude` is never touched); results are compared with `skills/`:
- `new` -> copy to `skills/<name>`, merge lock entry, add to bundle (prompt if no `bundle=` hint).
- `unchanged` -> skip. `changed` (upstream moved) -> shows file diff, asks. Re-running = update vendored.
- `protected` (name is your own skill, or vendored from another source) -> refused.
- `--yes` applies **new** skills only; updates always need interactive confirmation. `--dry-run` fetches but never writes.
- Scripts/executables in incoming files are flagged in the review. Nothing is committed. Lines are parsed strictly (only `npx skills add`, no shell); skill names must be explicit.
- Copy is verified against npx's hash before replacing; lock/marketplace are written in their existing format (1-line diffs).
