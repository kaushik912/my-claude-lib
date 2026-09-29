# my-claude-lib

Personal library of tested coding-agent skills, agents, commands and rules.

## Use in a project: `my-pick`

```
tools/my-pick/install.sh     # once per machine: venv + ~/.local/bin/my-pick
my-pick [project]            # checkbox UI; symlinks picks into the project
my-pick . --all              # everything (skills, agents, commands, rules)
my-pick . --all --kind skills,agents
my-pick . --all --copy       # copy instead of symlink
my-pick --list               # what's available + linked status
```

## Install agents into another project: `tools/agent-porter`

CLI to convert/install agent defs between Claude Code (`.claude/agents`) and
GitHub Copilot (`.github/agents`) formats, pulling from this repo (or any
`owner/repo`) via the GitHub API. See
[tools/agent-porter/README.md](tools/agent-porter/README.md).

Skills go to `.agents/skills` + `.claude/skills`; agents/commands/rules go to `.claude/`.

## Layout

- `.agents/skills/` — canonical content. Agent-agnostic skills live here directly; Claude-specific skills that have an agnostic fork also live here (e.g. `ticket-spec-agnostic`).
- `.claude/skills/` — Claude Code's view. Agent-agnostic skills are symlinks into `.agents/skills/<name>` (single source of truth, edit once). Skills that genuinely need Claude-only tools/conventions (e.g. `EnterWorktree`, slash-skill refs) live here as real files instead — `spec` and `ticket-spec` are the current examples.

## Installing into another project

```
npx skills add https://github.com/kaushik912/my-claude-lib --skill <name> --agent <agent>
```

e.g. `npx skills add https://github.com/kaushik912/my-claude-lib --skill ticket-spec-agnostic --agent github-copilot`

Omitting `--agent` auto-detects agents installed on your machine (not the same as `--agent '*'`, which force-installs to every supported agent).

Local path also works: `npx skills add /path/to/my-claude-lib --skill <name>`. Use `-l` to list available skills first.
