# my-claude-lib

Personal library of tested coding-agent skills, agents, commands and rules.

## Layout

- `skills/` — all skills (top-level so `gh skill` finds them). `my-pick` links them into projects as `.agents/skills/<name>` and `.claude/skills/<name>`.
- `.claude/{agents,commands,rules}` — Claude Code agents, commands, rules.
- `tools/my-pick` — pick items from this lib into a project.
- `tools/agent-porter` — convert/install agents between Claude and Copilot formats ([README](tools/agent-porter/README.md)).

## Use in a project: `my-pick`

```
tools/my-pick/install.sh     # once per machine
my-pick [project]            # checkbox UI; symlinks picks into the project
my-pick . --all [--copy]     # everything; --copy instead of symlink
my-pick . --pick caveman next-ticket   # non-interactive, additive (NAME or KIND/NAME)
my-pick . --preset root      # bundle from tools/my-pick/presets.json
my-pick . --remove NAME      # unlink
my-pick . --prune            # delete dead links into the lib (asks first; --yes to skip)
my-pick --list               # available items + linked status
my-pick --scan-back [--dry-run]   # merge edits made in projects/~/.claude back into the lib
```

Scan-back reports `NEW` and `DRIFT` items; you pick what to merge, then review with `git diff`. Nothing is auto-committed.

## Install elsewhere

```
gh skill install kaushik912/my-claude-lib <skill>
npx skills add kaushik912/my-claude-lib --skill <skill> --agent <agent>
/plugin marketplace add kaushik912/my-claude-lib     # Claude Code only
```
