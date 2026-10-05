---
name: e2e-grill
description: >-
  Brainstorms end-to-end test scenarios for a repo interactively, one category
  at a time (happy path first, then top edge cases), and saves them as BDD
  scenarios in docs/scenarios.md for review. Use when the user wants to
  explore or discover test scenarios, find edge cases worth testing, or
  document expected behavior before writing tests. No test code is written.
license: MIT
compatibility: "Requires Read/Grep/Glob/Write-equivalent tool access"
metadata:
  author: kaushik912
  version: "1.0.0"
  category: development
  tags: ["e2e", "scenarios", "bdd", "test-planning"]
---

Take a repo from "no scenario coverage" to a reviewable list of BDD scenarios,
one category at a time. Scenarios say *what* should happen, never *how* to
test it: no test framework, tool, or code. Never dump the whole app at once.

## 1. Scan

Use the path given, else the current directory. Find the entry points: API
endpoints (controllers/routes/handlers) and, if there is a UI, pages and user
flows. For each, note inputs and validation, auth guards, and failure paths
with their outcomes. Skim README/docs and existing tests so you don't
re-suggest what's covered. Never ask the user for facts the code answers.

If `docs/scenarios.md` exists, read it and report which categories are
explored and each scenario's status. Offer to add to a category or start a new
one.

## 2. Pick a category

Group entry points by resource, module, or user journey. Show a short numbered
list and ask which to explore.

## 3. Discuss

Plain-English happy path first: what the correct flow looks like. Then **at
most 5** edge cases that matter most, one line each on why. Pick from:
validation, auth, not found, conflict/idempotency, wrong state, error mapping,
boundary values, dependency failure, concurrency. Skip what doesn't apply or
is already covered. Money/data-safety and ambiguous behavior rank first. Flag
anything that is a guess about intended behavior.

## 4. Confirm and save

User drops, edits, or approves. Nothing is written before that. Then add the
approved scenarios to `docs/scenarios.md`, one `##` section per category, one
block per scenario:

```markdown
## Sign-up

### SCN-004: Email already taken
Status: proposed
Why: duplicate accounts break login
- Given a user exists with email a@x.com
- When a new user signs up with a@x.com
- Then the response is 409 with an "email taken" message
```

- IDs are `SCN-NNN`: next after the highest in the file, never reused or
  renumbered, even if the scenario is dropped later.
- New scenarios start as `Status: proposed`. Moving to `agreed` is a human
  decision (review by the team). Never set it yourself.
- Steps are plain English, no code, no tool names.
- Edit only the current category's section. Save before moving on, even if the
  user stops here.

Then ask whether to explore another category or stop.

## Guidelines

- Never write test code or edit `docs/scenarios.md` before the user confirms.
- Never show more than 5 edge cases in one batch.
- Statuses used: `proposed`, `agreed`, `implemented in <path>`. Only
  `proposed` is set here.
