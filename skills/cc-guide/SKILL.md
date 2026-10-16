---
name: cc-guide
description: >-
  Use when the user asks a question about Claude Code itself (CLI features, hooks,
  slash commands, MCP, settings, permissions, skills, plugins, IDE integrations,
  shortcuts), the Claude Agent SDK, the Claude API / Anthropic SDK, Claude Tag, or
  /skill-doctor ("Can Claude...", "How do I... in Claude Code"). Delegates to the
  built-in claude-code-guide agent on Haiku to save tokens.
license: MIT
compatibility: "Requires Claude Code with the built-in claude-code-guide agent"
metadata:
  author: kaushik912
  version: "1.0.0"
---

# cc-guide

Answer Claude Code / Agent SDK / Claude API questions via the built-in `claude-code-guide` agent, always on Haiku.

## Steps

1. If a `claude-code-guide` agent already ran this session, continue it with `SendMessage` (keeps context, stays on Haiku).
2. Otherwise spawn it with the `Agent` tool:
   - `subagent_type: "claude-code-guide"`
   - `model: "haiku"` — always, never any other model
   - `prompt`: the user's question verbatim, plus only the context needed to answer it
3. Relay the answer concisely. Don't pad or restate the whole agent output.

## Rules

- Never answer from memory; the guide agent has current docs.
- Never drop the `model: "haiku"` override. This is plain documentation work.
- Don't spawn extra agents (Explore, general-purpose) for these questions.
