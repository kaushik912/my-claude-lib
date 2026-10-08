# my-claude-lib

Personal library of tested coding-agent skills, agents, commands and rules.

## Layout

- `skills/` — all skills (top-level so `gh skill` finds them). `skill-sync` installs them into projects as `.agents/skills/<name>` and `.claude/skills/<name>`.
- `.claude/{agents,commands,rules}` — Claude Code agents, commands, rules.
- `tools/skill-sync` — install/pull/push skills between this lib and projects ([README](tools/skill-sync/README.md)).
- `tools/skill-inventory` — scan a tree for `.claude/skills` / `.agents/skills`; JSON of unique skills per project.
- `tools/agent-porter` — convert/install agents between Claude and Copilot formats ([README](tools/agent-porter/README.md)).

## Use in a project: `skill-sync` (skills only)

```
tools/skill-sync/install.sh        # once per machine
skill-sync install spec ticket-spec   # lib -> project (no names = picker)
skill-sync status | pull | push | remove <name>
```

## Install elsewhere

```
gh skill install kaushik912/my-claude-lib <skill>
npx skills add kaushik912/my-claude-lib --skill <skill> --agent <agent>
/plugin marketplace add kaushik912/my-claude-lib     # Claude Code only
```
