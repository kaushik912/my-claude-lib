# CLAUDE.md

## What this repo is

Personal library of coding-agent skills, agents, commands and rules — content, not an app. No build, lint or test suite. The only code is small CLIs/scripts under `tools/`.

## Layout

- `skills/<name>/SKILL.md` — canonical home of my skills. Edit here only. No `.agents/` or `.claude/skills/` here.
- `registry/` — vendored (third-party) skills + `skills-lock.json`. Add with `npx skills add <repo> --skill <name> -a claude-code github-copilot -y` run inside `registry/`; update with `skill-sync refresh`. Don't hand-edit skill files.
- `.claude/{agents,commands,rules}` — real files. Copy into projects with `skill-sync <cmd> --kind commands|agents|rules <names>`.
- `.claude-plugin/marketplace.json` — groups skills into installable plugin bundles, each with a `version`. Bump it when a bundle's skills change. **When creating a skill, add it to the matching bundle in the same change** (new bundle if none fits). Every dir in `skills/` must appear in some bundle.

## Tools

- `tools/skill-sync` — wraps the pinned `skills` CLI. `install`/`pull` lib → project, `push` project → lib (my skills only), `remove` uninstalls from a project, `refresh [name]` re-fetches one vendored skill (remove + add; interactive picker). Install: `./install.sh`; tests: `npm test`. See its README.
- `tools/agent-porter` — Node ≥20 CLI converting agents between `.claude/agents/*.md` and Copilot `.github/agents/*.agent.md`. `npm install` in that dir; usage in its README.
- `tools/skill-inventory` — scans a tree and reports skills per project.
- `tools/list-skills/` — bash script listing local skills, or a plugin's skills (`list-skills <plugin>`). `install.sh` / `uninstall.sh` link/unlink it in `~/.local/bin`.

## Conventions

- Skill frontmatter: `name`, `description` ("Use when ..."), `license`, `compatibility`, `metadata`. Model: `skills/mysql-query/SKILL.md`.
- Keep `description` ≲500 chars, trigger in the first sentence (listings truncate at 80). Leave vendored skills as is.
- Scripts live beside `SKILL.md`. Credential files (`db.cnf`, `atlassian.cnf`, `jira.cnf`) are gitignored — never commit.
- Skills are installed elsewhere (`gh skill install`, `npx skills add`, plugin marketplace), so keep them self-contained: no references outside their own dir.

## Personal rules

- Report info extremely concisely; sacrifice grammar.
- New skills go in this repo.
