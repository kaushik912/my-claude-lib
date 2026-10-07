---
name: jira-query
description: >-
  Use when the user asks about Jira issues/tickets/sprints — search, look up,
  create, or update (e.g. "find open tickets in ABC", "get issue ABC-123",
  "create a bug ticket"). Runs REST calls via jira.sh — no Atlassian MCP
  needed, just curl and a local credentials file.
license: MIT
compatibility: "Requires curl, jq; not tied to any MCP server"
metadata:
  author: kaushik912
  version: "1.0.0"
  category: development
  tags: ["jira", "atlassian", "cli", "rest"]
---
# Jira Query — Jira via CLI

## Overview

Call the Jira Cloud REST API straight from the CLI using `jira.sh`, without
an MCP server dependency. Credentials live in a config file you create from the
shipped `jira.cnf.example`, keep wherever you like (outside the repo is best) and
point to with `JIRA_CNF` — never inline on the command line (avoids leaking the API token into shell
history / process listing).

This is not read-only — issue creation/updates are a normal use case.
There's no method guardrail beyond GET/POST/PUT/DELETE; be deliberate before
issuing a POST/PUT (creates/mutates real tickets).

## Setup

```bash
export JIRA_API_TOKEN="your_api_token"   # add to ~/.bashrc to persist
cp jira.cnf.example /path/of/your/choice/jira.cnf   # anywhere, outside the repo is best
# fill in JIRA_SITE / JIRA_EMAIL; JIRA_TOKEN already references JIRA_API_TOKEN
chmod 600 /path/of/your/choice/jira.cnf
export JIRA_CNF=/path/of/your/choice/jira.cnf        # add to ~/.bashrc to persist
chmod +x jira.sh
```

Get an API token at https://id.atlassian.com/manage-profile/security/api-tokens.

## Usage

There is no default config location: `JIRA_CNF` must point at your config file
(see Setup).

```bash
# Search issues (JQL)
./jira.sh GET "/rest/api/3/search?jql=project=ABC AND status=Open"

# Get one issue
./jira.sh GET "/rest/api/3/issue/ABC-123"

# Create an issue
./jira.sh POST "/rest/api/3/issue" \
  '{"fields":{"project":{"key":"ABC"},"summary":"Test","issuetype":{"name":"Task"}}}'
```

## Trimming output (raw responses are huge)

Jira JSON objects run 50+ fields deep. Always pipe through `jq` to cut tokens
before showing the user.

```bash
# Search results -> key/summary/status
./jira.sh GET "/rest/api/3/search?jql=project=ABC" \
  | jq '.issues[] | {key, summary: .fields.summary, status: .fields.status.name}'

# Single issue -> key/summary/status/assignee
./jira.sh GET "/rest/api/3/issue/ABC-123" \
  | jq '{key, summary: .fields.summary, status: .fields.status.name, assignee: .fields.assignee.displayName}'
```

## Rules

- Requires `JIRA_CNF` pointing at a config file (no default location) —
  never pass the token inline.
- `JIRA_TOKEN` in `jira.cnf` may reference an already-exported env var (e.g.
  `JIRA_TOKEN="$JIRA_API_TOKEN"`) instead of a raw literal — `jira.cnf` is
  bash-sourced, so this expands normally.
- GET is safe to run freely for lookups. POST/PUT/DELETE mutate real Jira
  tickets — confirm with the user before issuing one unless they've
  explicitly asked for the create/update/delete.
- Jira API docs: `/rest/api/3/*`.
- Pipe output through `jq` (see above) before showing the user — don't dump
  raw Jira JSON into chat.

## Troubleshooting

- `ERROR: JIRA_CNF must point to an existing config file` — create the file from
  `jira.cnf.example` and `export JIRA_CNF=/path/to/jira.cnf`.
- `curl: command not found` / `jq: command not found` — install them
  (`apt install curl jq`, `brew install curl jq`, etc.).
- 401/403 from the API — check `JIRA_EMAIL`/`JIRA_TOKEN` in your `JIRA_CNF` file; token
  may be expired/revoked.
