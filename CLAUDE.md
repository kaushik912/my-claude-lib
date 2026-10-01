# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Personal library of coding-agent skills, agents, commands and rules — content, not an app. No build, lint or test suite. The only code is two small CLIs under `tools/`.

## Layout (symlinks matter)

- `skills/<name>/SKILL.md` — **canonical** location for all skills. Edit here only. No `.agents/` or `.claude/skills/` in this repo; `my-pick` creates those links in *target* projects. To use a skill while working inside this repo, run `my-pick . --kind skills` (local links, not committed).
- `.claude/{agents,commands,rules}` — real files (Claude agents, slash commands, rules); also the `my-pick` sources for those kinds.
- `.claude-plugin/marketplace.json` — groups skills into installable plugin bundles (`java-debugging`, `spec-ticketing`, `api-testing`, ...) by listing `./skills/<name>` paths. **Whenever a new skill is created in this repo, add it to the matching bundle there in the same change (create a new bundle if none fits) — don't wait to be asked.** Check with: every dir in `skills/` must appear in some bundle's `skills` list.
- `skills-lock.json` — hashes for skills vendored from third-party repos (e.g. caveman); don't hand-edit.

## Tools

- `tools/my-pick/my-pick.py` — pick lib items into a project via symlink. Install once with `tools/my-pick/install.sh` (creates `.venv`, links `~/.local/bin/my-pick`). Flags: `--list`, `--describe NAME` (full untruncated description), `--all`, `--copy`, `--kind`, `--scan-back` (merge edits from projects/`~/.claude` back into the lib; reports `NEW`/`DRIFT`, never auto-commits). Repo root is resolved relative to the script, so no config.
- `tools/agent-porter` — Node ≥20 CLI converting agents between `.claude/agents/*.md` and Copilot `.github/agents/*.agent.md`. `npm install` in that dir; usage in its README.

## Conventions

- Skill frontmatter: `name`, `description` (trigger-focused: "Use when ..."), plus `license`, `compatibility`, `metadata` (see `skills/mysql-query/SKILL.md` as the model). `my-pick --list` truncates descriptions at 80 chars; first sentence should carry the trigger.
- **Skill `description` ≤ 500 characters** (full text, after joining multi-line YAML). Longer ones must be rewritten shorter without losing the main idea (what it does + key trigger phrases). Check: `python3 tools/my-pick/my-pick.py --describe <name>` and count. Vendored skills (`skills-lock.json`) are exempt — don't edit them.
- Skills that ship scripts keep them beside `SKILL.md` (e.g. `mysql-query/dbq.sh`). Credential files (`db.cnf`, `atlassian.cnf`, `jira.cnf`) are gitignored — never commit them.
- Rules in `.claude/rules/` are loaded in every Claude session here: regression-testing (ask before writing a Bruno/RestAssured test after an API bug fix), security, spring, testing-style (Given/When/Then), node, python.
- Installed elsewhere via `gh skill install kaushik912/my-claude-lib <skill>`, `npx skills add ...`, or `/plugin marketplace add kaushik912/my-claude-lib` — so skills must stay self-contained (no references to files outside their own dir).

## Personal rules

- When reporting information, be extremely concise; sacrifice grammar for concision.
- New skills go in this repo (git-controlled): `/home/kaush/github_projs/my-claude-lib`.
- Python scripts: always use a venv. Never `--break-system-packages` or user-wide pip installs.
