---
name: e2e-implement
description: >-
  Turns agreed BDD scenarios from docs/scenarios.md into automated end-to-end
  tests using the project's own test tool (RestAssured, Bruno, Postman,
  Playwright, Cypress, ...). Use when the user wants to implement, automate, or
  write tests for scenarios that were already reviewed and agreed.
license: MIT
compatibility: "Requires Read/Grep/Glob/Bash/Write-equivalent tool access"
metadata:
  author: kaushik912
  version: "1.0.0"
  category: development
  tags: ["e2e", "scenarios", "bdd", "test-automation"]
---

Implement scenarios that are already written and agreed. This skill decides
*how* to test; the scenarios decide *what*. Never invent or change a scenario
here.

## 1. Pick scenarios

Read `docs/scenarios.md` (or the path the user gives). List scenarios with
`Status: agreed`, grouped by category, and ask which to implement. Skip
`proposed` ones: they are not reviewed yet. If the user names a `proposed`
scenario, say so and ask whether to go ahead anyway.

No scenario file: tell the user and stop.

## 2. Choose the test tool

Use what the project already has, and match its style, location, and naming:
look at existing tests, build files, and CI config. If several tools exist,
ask which one. If none exists, ask the user which to use. Suggest a common
default for the stack (e.g. RestAssured for Java/Spring, Bruno or Playwright
otherwise), never choose silently.

Check the app is runnable for tests: base URL, port, test profile, required
services. If it needs Docker or other heavy setup, ask before starting it.
A wrong port or base URL fails every test with a connection error, which is
not a real signal.

## 3. Draft

Translate each Given/When/Then into one test:

- Name or describe it from the scenario, and put the scenario ID (`SCN-NNN`)
  in a comment, tag, or docs field so test and scenario trace to each other.
- Given = setup, When = action, Then = assertion. Keep that order visible in
  the code or comments.
- Plain-English description where the tool supports one.
- If a test for the same condition already exists, extend it instead of
  duplicating.

Show the full file(s) and get approval before writing. Never write silently.
Creating a new test directory or collection needs a separate confirmation.

## 4. Run

Run the new test with the project's runner. Expected: it passes.

If it fails, work out why before touching anything:
- Test setup wrong (path, port, data, auth) → fix the test.
- App behaves differently from the agreed scenario → real bug. Report the
  scenario ID, expected vs actual. Do not change app code or the scenario
  unless the user asks.

## 5. Update the doc

After a passing run, set that scenario to `Status: implemented in <test path>`.
Leave every other scenario untouched. If the test is red because of a real
bug, leave the status as `agreed` and tell the user.

Ask whether to implement another `agreed` scenario or stop.

## Guidelines

- Never edit a scenario's Given/When/Then. Wrong or unclear scenario → tell the
  user to fix it in the doc.
- Never mark `implemented` without a passing run.
- Never write files, or start heavy services, without the confirmations above.
- Keep the scenario ID identical in the doc and the test.
