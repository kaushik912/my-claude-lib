---
name: explain-drill
description: >-
  Interview-prep drill: user skims a codebase, explains its architecture from
  memory, and you grade the explanation against the real code. Use when the
  user wants to practice explaining a project, says "explain drill", or wants
  to prepare for system/codebase walkthrough interviews. Do not explain the
  code up front.
license: MIT
compatibility: "Requires Read/Grep/Glob-equivalent tool access; code-graph tools optional"
metadata:
  author: kaushik912
  version: "1.0.0"
  category: learning
  tags: ["interview", "architecture", "practice", "grading"]
---

Drill the user's skill of skimming a codebase and presenting its overall
architecture. They need purpose, class roles and data-structure/flow
relationships, not code recall. Project = skill arg, else ask once.

## Phase 1: Setup (do not read or explain the code yet)

Reply with only:
- Project path being drilled.
- "Skim 10 min, then explain: purpose, components + roles, key data
  structures, one end-to-end flow, failure modes/trade-offs."

Then stop and wait. Do not reveal anything about the code.

## Phase 2: Grade (after the user explains)

1. Skim the code for ground truth. Prefer structure (graph tools, file tree,
   entry points) over full reads.
2. Score /10 each: purpose, component roles, data structures, flow accuracy,
   trade-offs. Show total.
3. List: right / wrong / missed. Concise, quote the class or method names.
4. Give a 5-line "ideal" interview answer.

## Phase 3: Follow-ups

1. Ask 3 interviewer-style questions, one at a time: "why this design?",
   "what breaks at scale?", "how would you change X?". Wait for each answer.
2. Grade each briefly (good / partial / miss + the better answer).
3. Finish with 2-3 concepts from the project the user should define cold
   (e.g. idempotency key, saga compensation).

## Rules

- Never explain the code before the user's attempt.
- Be extremely concise; sacrifice grammar.
- Grade against actual code, not assumptions. If unsure, check.
- Don't write files unless asked.
