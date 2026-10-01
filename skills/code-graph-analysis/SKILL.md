---
name: code-graph-analysis
description: >-
  Use for codebase analysis questions: "how does X work", "who calls Y", "what breaks if I
  change Z", "explain the architecture", "trace this flow", "find where X is defined", "impact
  of this diff", onboarding to an unfamiliar repo. Uses the codebase-memory-mcp knowledge
  graph (indexed code graph) instead of grep/glob/file-by-file reading. Checks the MCP is
  configured first; prompts to index the repo on first use.
license: MIT
compatibility: "Requires codebase-memory-mcp MCP server (add via mcp-init.py)"
metadata:
  author: kaushik912
  version: "1.0.0"
  category: analysis
  tags: ["mcp", "code-graph", "analysis", "call-graph", "impact-analysis", "architecture"]
---
# Code Graph Analysis (codebase-memory-mcp)

Tools appear as `mcp__codebase-memory-mcp__*`. The repo is parsed once into a graph
(functions, classes, routes, calls, imports). Queries then return structure directly, not
raw files.

## Why faster than grep/Read

- **One call, not many**: "who calls X" = 1 `trace_path`, not grep → read → grep → read loop.
- **Ranked + deduped**: BM25 search with structural boost, definitions first, tests last.
- **Compact output**: signatures/trees, not whole files → far fewer tokens.
- **Multi-hop answers**: transitive callers, blast radius, cross-service HTTP calls — impractical with grep.
- **Read only what matters**: `get_code_snippet` pulls one symbol's body; skip opening big files.

## Step 0 — Preflight (always, before anything else)

1. **MCP configured/active?** Check `mcp__codebase-memory-mcp__*` tools are available (load via
   ToolSearch if deferred). If missing: also check `.mcp.json` in cwd for `codebase-memory-mcp`.
   - Entry exists but tools absent → tell user to restart session / approve the server (`/mcp`).
   - No entry → **stop**. Tell user: run `mcp-init.py` in this project and pick
     `codebase-memory-mcp`, then restart session. Do not fall back silently to grep for a
     graph-style question — ask first.
2. **Indexed?** Call `list_projects`, find this repo (match root path to cwd).
   - Not listed → **ask user**: "Repo not indexed yet. Index this repo now? (first time only; takes a while on big repos)". On yes: `index_repository` with `repo_path` = cwd.
   - Listed → `index_status`. If stale (many commits since / user says code changed), offer re-index.
3. Note `project` name from `list_projects`; pass it to later calls.

If user forgot to index and asks an analysis question, don't just answer — prompt for indexing
first (step 2).

## Question → tool

| Goal | Tool |
|---|---|
| Orient in new repo | `get_architecture` (default compact; add `aspects:["routes","hotspots","layers","clusters"]`) |
| Find symbol / concept | `search_graph` `query="..."` (BM25) or `name_pattern`, `label`, `file_pattern` |
| Text/regex hit with graph context | `search_code` (grep + enrich) |
| Read one symbol's source | `search_graph` → `get_code_snippet(qualified_name)` |
| Callers / callees / deps | `trace_path` `mode=calls`, `direction=inbound\|outbound`, `depth` |
| How a value flows | `trace_path` `mode=data_flow`, `parameter_name` |
| Service-to-service (HTTP/async) | `trace_path` `mode=cross_service`; multi-repo: `index_repository mode=cross-repo-intelligence` |
| Blast radius of uncommitted/branch diff | `detect_changes` (`scope`, `base_branch`) |
| Custom multi-hop / aggregates | `query_graph` (Cypher; `get_graph_schema` first; always `LIMIT`) |
| Dead code / hubs / coupling | `search_graph` with `min_degree`/`max_degree`, or `query_graph` |
| Record decisions | `manage_adr` |

## Analysis recipes

- **Onboarding**: `get_architecture` → `aspects:["routes","clusters"]` → `search_graph` entry points → `trace_path` outbound on 1–2 key flows.
- **"What does feature X do"**: `search_graph query=X` → `get_code_snippet` top hit → `trace_path` outbound depth 2–3.
- **Pre-change impact**: `trace_path` inbound on target (`include_tests=true` to see test coverage) → summarize callers by module.
- **PR/diff review**: `detect_changes` → list impacted symbols/routes → flag untested ones.
- **Bug hunt**: `search_graph` symptom → `trace_path` inbound+outbound → `get_code_snippet` suspects only.
- **Dead code**: `search_graph max_degree=0 exclude_entry_points=true` (verify before claiming; reflection/DI can hide callers).

## Gotchas

- **Coverage caveat**: some files are skipped or only partially parsed. Before any
  "nothing calls this" / "exhaustive" claim, run `check_index_coverage` on the cited
  files/scopes. Otherwise say result is best-effort.
- **Dynamic dispatch** (reflection, Spring DI, proxies, string-built routes) may be missing edges. Confirm with `search_code` when result looks too empty.
- **Stale index**: graph reflects last index, not working tree. Re-index (`index_repository`) after big changes; `detect_changes` reads git diff directly.
- **Ambiguous names**: `get_code_snippet` with short name may return suggestions — use the full `qualified_name` from `search_graph`.
- Cap output: use `limit`/`depth`; add `LIMIT` in Cypher.
- Fall back to Read/Grep only for non-code files (configs, docs) or to verify a graph result.

## Reporting

Per user preference: extremely concise. Lead with the answer, list symbols as
`qualified_name (file)`, no narration of tool calls.
