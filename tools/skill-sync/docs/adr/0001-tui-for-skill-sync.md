# ADR 0001: TUI for skill-sync

- Status: Accepted. Implemented through step 4 (see Implementation order)
- Date: 2026-10-08

## Context

`skill-sync` (Node >= 20, ESM, ~576 LOC, one dep: pinned `skills` CLI) is flag-driven.
Only interactive bit: numbered picker in `bin/skill-sync.js` (`parseSelection` in `src/pick.js`).
Skills and `--kind commands|agents|rules` use two code paths and two locks
(`skills-lock.json`, `.claude/claude-lib-lock.json`). Bundles exist only in
`.claude-plugin/marketplace.json`; skill-sync ignores them.

Wanted from a TUI: status table -> select -> act; multi-select install across
kinds; diff preview before pull/push/remove; bundle-aware install.

## Decisions

1. **TUI is a thin view over existing code. No parallel logic.**
   TUI never copies/hashes/edits locks. It builds the same args the CLI builds
   and calls the same functions (`commands.js`, `files.js`). Anything the TUI can
   do must be doable by a CLI invocation.
2. **Non-interactive CLI stays authoritative and unchanged in behavior.**
   Bare `skill-sync` on a TTY -> TUI. Any args or no TTY -> current CLI.
3. **Features land as CLI flags first, TUI second.**
   - `status --all-kinds` (skills + agents + commands + rules, one list)
   - `install --bundle <name>` (bundle = selection shortcut; expands to skill
     names; no new lock concept; skills only)
   - `--diff` with `--dry-run` (diff preview; TUI preview pane reuses it)
4. **Shared pieces** (used by CLI and TUI alike):
   - `src/ops.js`: one dispatcher `command + kind -> function`, plus `statusAll`
     (replaces the `--kind` branching in `bin`).
   - `src/bundles.js`: parse `marketplace.json`, join with item state.
   - Items keyed `kind/name` (avoids skill `spec` vs rule `spec` clash).
5. **Lib-owner ops** (`refresh`, `push --adopt`) stay separate from the
   project TUI; shown only when cwd = lib. Vendored skills: `push` disabled.
6. **Testing strategy**
   - Reducer + render split: `reduce(state, key) -> state`, `render(state) -> string`.
   - Unit-test reducer; snapshot-test render (ANSI stripped).
   - Parity test: TUI selection -> fn args == equivalent CLI flags.
   - Prompt fn injectable (no TTY in tests).
   - No tmux / node-pty / external tools: tests stay self-contained in Node.
     Drive the TUI in-process by injecting `input` (PassThrough stream of keypresses)
     and `output` (capture stream) instead of real stdin/stdout.
7. **Diff preview** = `dryRun: true` + pure-Node line diff (no `diff`/`git` dependency) of
   installed vs source. Useful for pull (conflicts), push, remove (files lost).

## Options considered (library)

| Option | Verdict |
|---|---|
| Raw readline + ANSI | zero-dep; DIY keys/resize |
| @clack/prompts | leading candidate: small, multiselect/confirm; prompt-flow only |
| Ink | best testing (`ink-testing-library`), full-screen; heavy for this size |
| blessed | unmaintained; rejected |
| fzf/gum shell-out | external binary; rejected for portability |
| Web UI | not a TUI; rejected |

## Resolved (2026-10-08)

- Style: **prompt-flow** (status -> action -> multiselect -> preview -> confirm), not a dashboard.
- Library: **@clack/prompts**, pinned (`1.8.1`, Node >= 20.12). Loaded lazily, only for the TUI path.
- Diff preview: **in v1** (reuses `withDiff`).
- Tests (supersedes decision 6 reducer/render split): clack owns rendering, so the flow is
  tested with an injected prompt adapter (`fakeUi`) against real temp lib/project dirs.
  Pseudo-terminal smoke done once by hand (Python `pty`); no tmux/node-pty in the repo.
- Still deferred: bundles for agents/rules (needs new metadata); dashboard mode.

## Kind grouping (2026-10-08)

Flat multiselect gets long (Install lists every `new` lib item, incl. vendored skills). Decided:

- Kind picker step before the list: All / Skills / Commands / Agents / Rules.
- "All" shows grouped list (clack `groupMultiselect`, header per kind); a kind shows its flat list.
- Picker skipped when only one kind has items.
- Bundles (Install) stay on top: own first group in "All", top of the skills list in the skills view. Bundles count as kind `skills` for the skip rule.
- Text filter: flat lists use clack `autocompleteMultiselect` (type to filter, Tab selects). Clack has no grouped autocomplete, so "All" stays unfiltered; pick a kind to filter.
- TUI stays a thin view: `buildCalls` already groups by kind, so selection handling is unchanged.
- Status: built (`groupByKind`, `selectValues` in `src/tui.js`; `groupMultiselect` in the clack adapter).

## Implementation order

1. DONE: `src/ops.js` (`dispatch`, `statusAll`) + `status --all-kinds`; `bin` uses it.
2. DONE: `src/bundles.js` + `install --bundle` (bundle-state join for the TUI tab comes with step 4)
3. DONE: `--diff` (`src/diff.js` pure-Node line diff, `src/preview.js` `withDiff`; rows get a `diff` string the TUI pane can reuse)
4. DONE: TUI (`src/tui.js` flow + `buildChoices`/`buildCalls`, `src/ui-clack.js`, `src/format.js` shared with CLI output)
5. DONE: flow tests with injected prompts (`test/tui.test.js`); no external tools

## Consequences

+ One behavior, two front-ends; CLI tests cover most TUI risk.
+ TUI choice (library) is reversible: it only touches the view layer.
- Small refactor of `bin/skill-sync.js` up front.
