---
name: next-ticket
description: Use to resume or advance an epic made by `ticket-split` - picks the next ready ticket from tickets/INDEX.md, runs it through `ticket-spec` in its own worktree, and records status. Safe to re-invoke after a crash or in a fresh session. Works in any coding agent with file access and a shell.
disable-model-invocation: true
---

Orchestrator for an epic. **Code lives in worktrees; tracking lives in the main checkout** on the epic branch. All state is on disk (`tickets/INDEX.md`, each worktree's `.spec/<slug>/tasks.md`), so re-invoking is always the resume path.

Invoked as `/next-ticket` or `/next-ticket <ticket-id>`. An explicit id runs that ticket (parallel runs of independent tickets).

## Stage 1: Locate

- Find the main checkout: first path from `git worktree list`. `cd` there. Read `tickets/INDEX.md` from it; edit `INDEX.md` only from it.
- Confirm the branch is `epic/*`. Otherwise stop and report.
- `tickets/PAUSED` exists: stop, report it.
- Working tree dirty: stop and report. Merges and worktree creation need it clean.

## Stage 2: Select

Priority, first match wins:

1. Id given in args: use it, after checking its `depends_on` are all `done`.
2. A `doing` ticket: resume it. Several `doing`: ask which.
3. First `todo` ticket whose `depends_on` are all `done`.
4. Nothing selectable: report why (all `done`: epic complete; else list `blocked` tickets and what they wait on). Stop.

A resumed `doing` ticket whose worktree's last commit and `tasks.md` are both older than 30 minutes is **stale**: say so, then resume it anyway (resuming is safe).

## Stage 3: Run

1. `attempts` >= 3: set `blocked`, note the cause in the commit message, stop and report. A human decides.
2. Find the worktree: `git worktree list`, entry on branch `worktree-<slug>`. Found (under `.agents/worktrees/` or `.claude/worktrees/`, e.g. made by `claude -w`): use the path it reports. None: `git worktree add .agents/worktrees/<slug> -b worktree-<slug> <epic-branch>`. Ensure `.agents/worktrees/` and `.claude/worktrees/` are gitignored.
3. Set `doing`, bump `attempts`, fill `branch` (`worktree-<slug>`) and `worktree` (the path from step 2) in `INDEX.md`. Commit: `INDEX: <id> doing`.
4. `cd` into the worktree and follow `ticket-spec/SKILL.md` with `tickets/<id>.yaml`. It sees the right worktree and proceeds to Resume.

Done when `ticket-spec` reports wrap-up or stops on an unresolved failure.

## Stage 4: Close

- `.spec/<slug>/tasks.md` all `[x]`: report branch and the verify command, then ask the user to confirm the merge. On yes, from the main checkout:
  ```
  git merge --no-ff worktree-<slug>
  git worktree remove <worktree path from INDEX.md>
  ```
  Set `done`, clear `worktree`, commit `INDEX: <id> done`. A dependent ticket starts only after `done`, because only then does the epic branch hold the code.
- On no: leave the ticket `doing`, stop.
- Merge conflict: stop, report the files, leave the ticket `doing`. Never resolve it silently.
- `ticket-spec` failed: leave `doing`, report where it stopped. The next `/next-ticket` retries and bumps `attempts`.

## Stage 5: Report

One line: ticket id, new status, next selectable ticket. Then stop. One ticket per invocation keeps context small; the user runs `/next-ticket` again after `/clear`.

## Pause

`touch tickets/PAUSED` stops selection (Stage 1); delete it to continue.
