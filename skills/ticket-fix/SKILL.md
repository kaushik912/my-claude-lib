---
name: ticket-fix
description: Use when fixing a bug from a YAML bug-ticket file in its own git worktree, unattended or gated, or when running several bug tickets in parallel. Works in any coding agent with file access and a shell.
disable-model-invocation: true
---

Runs one bug ticket through four stages inside a dedicated worktree named after the bug, writing to `.spec/<slug>/`: `repro.md` -> `diagnosis.md` -> `tasks.md` -> fix. Each artifact carries `status: draft` or `status: approved` in its frontmatter; `tasks.md` items are `- [ ]` / `- [x]`. Trust only what's on disk, never memory of an earlier turn.

**Iron rule:** no fix without a reproduction, and no fix without a failing test that captures it. If the bug can't be reproduced, stop and report — never guess a fix, even with `auto_approve: true`.

## Input

Path to a ticket YAML, e.g. `tickets/BUG-12.yaml`. No path -> exactly one `*.yaml` under `./tickets/`; several -> ask which.

**Freeform text instead of a path** and no ticket resolves: don't author one from assumptions. Ask for repro steps, expected vs actual behavior, and whether to run unattended. Write `tickets/<slug>.yaml` only after the user confirms.

```yaml
id: BUG-12
slug: null-email-500       # kebab-case, describes the bug — becomes worktree/branch name
title: Signup 500s on null email
repro: |
  1. POST /signup with {"email": null}
expected: 400 with a validation message
actual: 500 NullPointerException
suspected_area: SignupController   # optional hint, verify — don't trust
auto_approve: false        # true = flip status:approved at gates, unattended
```

Default `auto_approve` to `false` when authoring; `true` is an explicit opt-in. `slug` is mandatory; if missing, slugify `title` and write it back. Letters, digits, dots, underscores, dashes only.

## Stage: Worktree (before everything else)

Confirm the right worktree before touching `.spec/`. A worktree at `.agents/worktrees/<slug>` or `.claude/worktrees/<slug>` (or branch `worktree-<slug>`) is the right one:

- **Already there**: cwd is under either path -> proceed to Resume.
- **Resuming from elsewhere**: path exists but session isn't in it -> `git worktree list`, then `cd` into it (`EnterWorktree(path: ...)` if that tool is available).
- **Starting fresh**: `git worktree add .agents/worktrees/<slug> -b worktree-<slug>`, then `cd` into it (or `EnterWorktree(name: <slug>)` if available).
- Ensure `.gitignore` ignores the worktree dir used.

Launch shortcut: `git worktree add ...` + `cd`, then run your agent there with this skill and the ticket path. Claude Code: `claude -w <slug>`.

## Resume

Read `.spec/<slug>/` and jump to the first stage not done:

1. No `repro.md`, or `status: draft` -> **Repro**.
2. `repro.md` approved, no `diagnosis.md` or `status: draft` -> **Diagnose**.
3. `diagnosis.md` approved, no `tasks.md` -> **Tasks**.
4. `tasks.md` has any `- [ ]` -> **Implement** from the first unchecked.
5. All `- [x]` -> **Wrap-up**.

State the stage you're resuming into and why before starting it.

## Stage: Repro

Write `.spec/<slug>/repro.md` (`status: draft`) from the ticket: `## Steps`, `## Expected`, `## Actual`. Then actually reproduce it: run the steps against the code and capture the real output. Record it under `## Observed`.

- Observed matches `actual` -> reproduced; go to approval.
- Doesn't match, or can't be run -> set `status: blocked`, report what you tried and what you saw, and stop. Do not continue.

Approval: if `auto_approve: true` flip to `approved` and continue; else show it and wait for explicit approval (a read without objection is not approval).

## Stage: Diagnose

Find the root cause, not the symptom. Form a hypothesis, test it against the code or a run, and repeat until evidence confirms it. (If `superpowers:systematic-debugging` is available, use it.) Write `diagnosis.md` (`status: draft`):

```
## Root cause      # one paragraph, names the file/function and why
## Evidence        # what you ran/read that confirms it
## Fix approach    # smallest change that fixes the cause
## Risk            # what else could be affected
```

Keep the fix minimal — no refactors, no unrelated cleanup. Approval same as Repro.

## Stage: Tasks

Write `tasks.md` (`status: draft`), in this order:

```
- [ ] Write a failing test that reproduces the bug
- [ ] Fix: <one-line from Fix approach>
- [ ] Run the full test suite; confirm no regressions
```

Write the test through the seam the repo's existing tests already use — don't introduce a new test style. Add tasks only if the diagnosis calls for them (e.g. a data migration). Approval same as Repro, then start Implement.

## Stage: Implement

One task at a time, top to bottom. The failing test must fail **for the reason in `repro.md`** — not a typo or setup error; run it and confirm. Then apply the minimal fix, run it green, then the full suite. Check each box in `tasks.md` immediately.

Always commit after each task passes: `<ticket id>: <task>`. This is a local worktree branch; committed history is what makes a killed run resumable.

If the fix fails after two honest attempts, or the diagnosis proves wrong: set `diagnosis.md` back to `status: draft` with what you learned, and stop for a human. Don't stack more guesses.

## Stage: Wrap-up

When all boxes are `[x]`, report: root cause in one line, worktree path and branch, and the literal command that runs the new regression test. Leave the worktree as is — never `git worktree remove`; if you used `EnterWorktree`, exit with `ExitWorktree(action: "keep")`. Merge and cleanup are the user's.

## Parallel usage

One ticket per terminal, each in its own worktree (see Worktree stage). State lives under `.spec/<slug>/` on that branch, so runs never cross-talk, and re-invoking after an interrupt resumes from disk. Review and merge each branch manually, then `git worktree remove <path>`.
