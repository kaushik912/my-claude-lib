---
name: ticket-split
description: Use when a request is too big for one ticket (e.g. "build an ecommerce store with frontend and backend") and must be split into many dependent `ticket-spec` tickets plus a tracking index. Companion to `ticket-spec` and `next-ticket`. Works in any coding agent with file access and a shell.
disable-model-invocation: true
---

Turns one large request into an **epic**: shared spec, API contract, many small tickets, and `tickets/INDEX.md`. This is the only place the epic is brainstormed. Tickets come out complete, so `ticket-spec` never interviews again. Execution is `next-ticket`'s job.

Everything the next session needs lands on disk and is committed. Trust disk, never memory.

## Output layout

```
docs/spec.md                 # problem, goal, non-goals, stack, entities, slice list
docs/api-contract.md         # endpoints, schemas, errors (or openapi.yaml)
tickets/TICKET-001.yaml      # ticket-spec schema, every field filled
tickets/INDEX.md             # status + dependency table (single source of truth)
```

Branch: `epic/<epic-slug>`, created from the current branch. Ticket worktrees branch from it, and finished tickets merge back into it.

## Resume

Re-invoked with `docs/spec.md` present: read `docs/`, `tickets/`, `INDEX.md`, jump to the first undone stage below. Ask before overwriting anything already written.

## Stage 1: Interview

If `superpowers:brainstorming` is available, run it for this stage. Otherwise interview directly, one question at a time, until every item is answered:

- Problem, goal, non-goals.
- Users and core flows.
- Stack, one choice per layer (backend, frontend, DB, auth).
- Testing: `testing_seam` (`layered` | `single`) and `api_docs` (`true` | `false`).
- `auto_approve` for the generated tickets. Recommend `true`: the slices get approved in Stage 2, so per-ticket gates repeat that review. Use `false` when the user wants to review each plan.

Done when each acceptance criterion you can foresee is testable (an observable behavior, not "works well").

## Stage 2: Slices

Propose the ticket list as a table: id, slug, one-line goal, depends_on. Iterate until the user approves it.

Slice rules:
- **Vertical**: one user-visible capability per ticket (catalog, cart, checkout), cutting through backend and frontend. Split a ticket into backend and frontend halves only when it is too big to finish in half a context.
- **TICKET-001 is contract + scaffold**: repo layout, test runner, CI stub, `docs/api-contract.md`. Every other ticket depends on it, so frontend and backend tickets share one contract.
- **Sized to finish in half a context**: about 3-6 tasks, one concern, testable alone.
- **Dependencies explicit**: a ticket lists a dependency only when it needs that ticket's code. Independent tickets stay independent, so they can run in parallel.
- **Order**: dependencies first, then by user value.

Done when the user has said yes to the table.

## Stage 3: Spec and contract

Write `docs/spec.md` (section format as in `spec` skill's Spec stage, plus the approved slice table) and `docs/api-contract.md`. The contract names every endpoint the slices share, with request/response shapes and error codes.

Done when every endpoint a ticket's acceptance criteria mention appears in the contract.

## Stage 4: Tickets and index

For each slice write `tickets/<id>.yaml` in `ticket-spec`'s schema with **every field filled**: `id`, `slug`, `title`, `problem`, `goal`, `non_goals`, `acceptance`, `stack_notes`, `testing_seam`, `api_docs`, `auto_approve`. In `stack_notes` point at the relevant `docs/` sections instead of restating them. In `non_goals` name what neighbouring tickets own.

Write `tickets/INDEX.md`:

```
| id | slug | title | status | depends_on | branch | worktree | attempts |
|----|------|-------|--------|------------|--------|----------|----------|
| TICKET-001 | scaffold | Contract + scaffold | todo | - | | | 0 |
| TICKET-002 | catalog | Product catalog | todo | TICKET-001 | | | 0 |
```

Status values: `todo | doing | done | blocked`. `INDEX.md` is the only place status and dependencies live.

## Stage 5: Commit

```
git switch -c epic/<epic-slug>
git add docs tickets
git commit -m "epic <epic-slug>: spec, contract, tickets"
```

Commit before any worktree exists, so each worktree contains `tickets/<id>.yaml`.

Wrap-up: report the epic branch, ticket count, and the next command: `/next-ticket`.
