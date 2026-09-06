# agent-porter

Converts and installs agent definitions between Claude Code's `.claude/agents/*.md`
subagent format and GitHub Copilot's `.github/agents/*.agent.md` custom-agent format.
Fills the gap `npx skills add` (vercel-labs/skills) leaves — that tool installs Skills,
never Agents.

## Install

```bash
git clone https://github.com/kaushik912/claude-code-tooling.git
cd claude-code-tooling/agent-porter
npm install
npm link   # optional: makes `agent-porter` runnable directly
```

### Uninstall

```bash
npm unlink -g agent-porter   # removes the linked `agent-porter` command
rm -rf node_modules          # optional: drop installed deps
```

`npm link` only creates symlinks (nothing gets copied elsewhere), so `npm unlink -g`
fully removes the CLI from your `$PATH`. Deleting the `agent-porter/` directory itself
also breaks the link (it points back here), so unlink first if you're about to delete
the repo.

## Usage

### Convert — local directory/file, either direction

```bash
agent-porter convert --src claude --dest copilot
agent-porter convert --src claude --dest copilot --in .claude/agents --out .github/agents --dry-run
agent-porter convert --src copilot --dest claude --file some-agent.agent.md --out .claude/agents
```

`--in`/`--out` default to `.claude/agents` / `.github/agents` under the current
directory. `--dry-run` prints the plan without writing. `--force` overwrites existing
output files (default: skip + warn on collision).

### Install — pull from a public GitHub repo (defaults to [my-claude-agents](https://github.com/kaushik912/my-claude-agents))

```bash
agent-porter install --agent doc-writer
agent-porter install --agent doc-writer --dest copilot
agent-porter install --all --dest copilot
agent-porter install --repo someone-else/their-agents --agent foo   # override the source repo
```

`--repo` defaults to `kaushik912/my-claude-agents`. Source repos are expected to hold
agents in Claude format (default path `.claude/agents`, override with `--path`).
`--dest claude` (default) copies as-is; `--dest copilot` converts on the way in. No
lockfile / drift tracking in v1 — installs are one-shot; re-run to re-fetch (respects
`--force`).

## Field mapping caveats

`description` and the prompt body convert cleanly both ways. `tools` and `model` are
best-effort — Copilot's tool vocabulary is large and inconsistent in the wild, so only
a small, explicit mapping table is used; anything unrecognized is dropped with a
printed warning rather than guessed. `memory` (Claude-only) and `user-invocable`/
`argument-hint` (Copilot-only) have no cross-format equivalent and are always dropped
with a warning.
