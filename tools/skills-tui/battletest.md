# skills-tui battletest (P0 manual checks)

Absolute minimums that must work. Run top to bottom; also builds muscle memory.
All non-interactive steps were verified; TUI steps (T3-T5, D3, V4) need a real terminal.

## Setup

```bash
cd ~/github_projs/my-claude-lib && git pull
tools/skills-tui/install.sh                      # venv + ~/.local/bin/skills-tui
tools/skills-tui/.venv/bin/pip install -q -r tools/skills-tui/requirements-dev.txt
tools/skills-tui/.venv/bin/python -m pytest -q tools/skills-tui   # expect: all pass

export R=/tmp/somerandomfolder; mkdir -p $R/proj $R/proj2
L=~/github_projs/my-claude-lib
mkdir $R/lib-copy && cp -r $L/skills $L/skills-lock.json $L/vendors.txt $L/.claude-plugin $L/.claude $R/lib-copy/
(cd $R/lib-copy && git init -q && git add -A && git commit -qm base)   # so `git diff` works
```

`lib-copy` is a throwaway copy of the lib: doctor/vendor tests never touch the real one.

## T. Install (project: `$R/proj`)

- **T1 Catalog:** `cd $R/proj && skills-tui --list`
  - ~39 rows: `skills/...` marked `mine`/`vendored`, plus `rules/`, `commands/`, `agents/`. No `*` yet.
- **T2 Profile, no TUI:** `skills-tui --profile core --no-tui`
  - `add: skills/cavewhat, skills/karpathy-guidelines`; both dirs under `.claude/skills/`.
  - `skills-tui --list | grep '^\*'` shows them.
- **T3 TUI flow:** run `skills-tui`
  1. Enter skips profiles.
  2. Menu shows `skills (2/23)`, `rules (0/8)`, `commands (0/1)`, `agents (0/7)`.
  3. Enter on `rules`, type `sec` (filter), Space on `security`, Enter (back). Count -> `rules (1/8)`.
  4. Down to `✔ Apply`, Enter, `y`.
  - Expect `.claude/rules/security.md`.
- **T4 Untick removes:** `skills-tui` -> `skills` -> untick `cavewhat` -> Enter -> Apply -> `y`.
  - `remove: skills/cavewhat`; dir gone.
- **T5 Cancel is safe:** `skills-tui` -> `✖ Cancel` (or Ctrl-C at the menu). Nothing changes.
- **T6 Mixed kinds are real files:**
  `skills-tui --pick rules/spring agents/debugger commands/skills-used --no-tui && ls -l .claude/rules .claude/agents .claude/commands`
  - No `->` symlink arrows.
- **T7 Idempotent:** re-run T2 -> `nothing to do`.
- **T8 Dry run:** `skills-tui --pick spec --no-tui --dry-run` -> prints the `npx ...` command, installs nothing.
- **T9 Guards:**
  - `skills-tui --pick nope --no-tui` -> `error: unknown item: nope`, exit 2.
  - `skills-tui --pick rules/spring --no-tui --global` -> `error: rules: --global not supported (project-only)`, exit 2.

## D. Doctor (skills lock health)

- **D1 Healthy:** `cd $R/proj && skills-tui --doctor --yes` -> `healthy: nothing to fix`.
- **D2 Break project, report:**
  ```bash
  echo x >> .claude/skills/karpathy-guidelines/SKILL.md          # modified
  rm -rf .claude/skills/cavewhat                                 # dangling (if still installed)
  cp -r $L/skills/spec .claude/skills/spec                       # untracked
  skills-tui --doctor --yes --dry-run
  ```
  - Expect `modified`, `dangling`, `untracked`, then `nothing to apply` (none has a recommended fix).
- **D3 Interactive fix:** `skills-tui --doctor` (real terminal).
  - Per issue choose `restore from lib` / `keep as is` / `adopt`; confirm `y`.
  - Re-run D1: only what you kept remains.
- **D4 Lib-side drift (outdated + orphan):**
  ```bash
  cd $R/proj2
  skills-tui --lib $R/lib-copy --pick mysql-query debug-mode --no-tui
  echo x >> $R/lib-copy/skills/mysql-query/SKILL.md ; rm -rf $R/lib-copy/skills/debug-mode
  skills-tui --lib $R/lib-copy --doctor --yes --dry-run
  ```
  - Expect `orphan debug-mode`, `outdated mysql-query`; plan `update: mysql-query`, `delete: debug-mode`.
- **D5 Apply recommended:** D4 without `--dry-run`; a second `--doctor --yes` says `healthy`.
- **D6 No terminal:** `skills-tui --doctor </dev/null` -> `error: --doctor needs a terminal...`, exit 2.

## V. Vendor (always against `lib-copy`)

- **V1 Report only:** `cd $R/lib-copy && skills-tui --lib $R/lib-copy --vendor --dry-run`
  - `caveman: changed` (README.md, SKILL.md); `caveman-commit`, `caveman-stats`, `debug-mode` unchanged.
  - `-g` shown as an ignored flag. `git status --short` is empty.
- **V2 `--yes` adds new skills only:**
  ```bash
  echo 'npx skills add JuliusBrussee/caveman --skill caveman-compress  # bundle=caveman' >> vendors.txt
  skills-tui --lib $R/lib-copy --vendor --yes
  git status --short; git diff skills-lock.json .claude-plugin/marketplace.json
  ```
  - `caveman-compress` added, scripts flagged with a warning.
  - `caveman` shows `skipped: --yes never applies updates`.
  - Diff is small: a lock entry plus one marketplace line.
- **V3 Strict parsing:** `echo 'rm -rf /' >> vendors.txt; skills-tui --lib $R/lib-copy --vendor --yes`
  - `error: vendors.txt: line N: only `npx skills add ...` lines are allowed`, exit 2, nothing runs. Remove that line after.
- **V4 Interactive update:** `skills-tui --lib $R/lib-copy --vendor`
  - Answer `y` to `Update caveman?`. `git diff --stat` shows `skills/caveman/*`. Nothing is committed.
- **V5 Protected names:** point a vendors line at one of your own skill names (e.g. `--skill karpathy-guidelines`).
  - Expect `protected (exists in lib and is not vendored)`; no change.

## U. Uninstall

- `tools/skills-tui/uninstall.sh` -> link and venv removed; `command -v skills-tui` is empty.
- Run it twice (safe), then `install.sh` again.

## Muscle-memory cheat sheet

- Menu: `Enter` opens a kind. `Space` toggles. Typing filters. `Enter` goes back. `✔ Apply` then `y` installs.
- `--dry-run` first on anything new.
- `--doctor` and `--vendor` are rare-use; `--yes` is the cautious non-interactive mode for both
  (doctor: recommended fixes only; vendor: new skills only).
