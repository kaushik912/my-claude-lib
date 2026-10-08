# skill-sync

Thin wrapper over [`npx skills`](https://github.com/vercel-labs/skills) that keeps skills in sync between this repo (`my-claude-lib`, the central registry) and your projects. Skills only.

```
my-claude-lib/skills/<s>          (mine, hand-edited)       \
                                                              >--install/pull-->  project/.agents/skills/<s>  (+ .claude symlinks)
my-claude-lib/registry/.agents/skills/<s>  (vendored)   /                            |
        ^                                                                                  |
        +------------------------------ push (mine only) ---------------------------------+
```

- **Mine** live in `skills/` — edit them there. No mirror, no lock entry, nothing to refresh.
- **Vendored** are installed by `npx skills add <repo> ...` run inside `registry/`: real files in `registry/.agents/skills/`, `registry/.claude/skills/` symlinks, `registry/skills-lock.json`.
- **Project** installs get the same layout: real files in `.agents/skills/`, `.claude/skills/` symlinked. Git in the project handles review/accept/reject.

## Requirements

Node >= 20. One dependency: the `skills` CLI, pinned in `package.json` (`./install.sh` runs `npm install`; ~0.1s per call). The tool always uses this local copy (no global or `npx` fallback; if missing it errors with "run npm install"). Bump the pinned version deliberately: `skill-sync` relies on the CLI's `computedHash` algorithm and install layout (the e2e test catches a break).

## Setup

```bash
./install.sh      # symlinks ~/.local/bin/skill-sync -> bin/skill-sync.js
./uninstall.sh    # removes only that symlink
```

Lib location (flag > env > default): `--lib` > `SKILL_SYNC_LIB` > the repo this tool lives in.

## Commands

Project commands run from the **project** dir. All take optional skill names, `--dry-run`, `--force`.

| Command | Does |
|---|---|
| `install [skills...]` | lib -> project. Mine come from `skills/`, vendored from `registry/.agents/skills/`. No names = numbered picker. |
| `pull` | lib -> project. Updates installed skills that changed upstream; also lists skills in lib you haven't installed (`new`). |
| `status` | per-skill state of the project vs lib, plus `new` skills. Read-only. |
| `remove <names...>` | uninstall from the project (`skills remove <name> -y`: files, `.claude` symlink, lock entry). Errors if not installed. `--dry-run` reports only. Also clears `missing-upstream` leftovers. |
| `push` | project -> lib. Copies locally edited skills into `skills/` (uncommitted; review with `git diff`). |
| `refresh` | lib owner only. Re-fetches ONE vendored skill from upstream: reads `source` from the lock, then `skills remove <name> -y` + `skills add <source> --skill <name> -y` in `registry/`. No name = interactive picker. `--dry-run` prints the commands only. If add fails after remove, the error shows the restore command. |

### Typical flows

```bash
# new project
cd ~/proj && git init && skill-sync install spec ticket-spec

# later: what changed / what's new?
skill-sync status
skill-sync pull --dry-run && skill-sync pull      # then git diff, commit

# improved a skill in the project -> send it back
skill-sync push --dry-run && skill-sync push      # then review + commit in my-claude-lib
skill-sync pull                                   # settles the project's lock (converged -> in-sync)

# lib owner: add a new skill of mine
mkdir skills/foo && $EDITOR skills/foo/SKILL.md   # that's it; projects see it as `new`

# lib owner: add a vendored skill / update vendored ones
cd registry && npx skills add owner/repo --skill name -a claude-code github-copilot -y && cd ..
skill-sync refresh [name]   # one skill; picker if no name; review git diff, commit
```

## States

State is a three-way compare of: source hash now, `computedHash` in the project's `skills-lock.json` (at install), and the installed copy's hash now. Hash = SHA-256 of all files in the skill folder (same as `npx skills`).

| State | Meaning | pull | push |
|---|---|---|---|
| `in-sync` | nothing changed | skip | - |
| `upstream` | source changed | update | - |
| `local` | installed copy edited | skip | push (mine only) |
| `conflict` | both changed | skip (`--force` overwrites) | skip if lib changed since install (`--force` overwrites) |
| `converged` | both changed to the same content | refresh lock | skip |
| `new` | in lib, not installed | listed only (`install` it) | - |
| `missing-upstream` / `missing-local` | folder gone | skip | - |

## Push rules

- Only skills that exist in `my-claude-lib/skills/` are pushed. Vendored skills live in `registry/`, so they are skipped (`skipped (not in lib/skills)`).
- Never commits. A brand-new skill authored in a project (no lock entry) is not pushed — put it in `skills/` by hand.

## Why re-add instead of `npx skills update` for projects

`update` doesn't handle local-path sources, so `pull` re-runs `npx skills add <lib folder> --skill ... -a claude-code github-copilot -y`, which overwrites the copy and refreshes the lock. A universal agent (`github-copilot`) makes the CLI keep real files in `.agents/skills/` and symlink `.claude/skills/`; `claude-code` alone would make a plain copy in `.claude/skills/`.

Vendored skills *do* come from GitHub sources, but `npx skills update` is slow and flaky, so `refresh` does remove + add per skill instead.

## Layout

```
bin/skill-sync.js   CLI arg parsing + printing
src/hash.js         directory hash (matches npx computedHash)
src/lock.js         read skills-lock.json
src/sources.js      mine (skills/) + vendored (registry/.agents/skills) lookup
src/plan.js         classify() three-way state
src/commands.js     install / uninstall / pull / status / push / refreshVendored
src/npx.js          the only place that shells out to `npx skills`
src/config.js       lib resolution
src/pick.js         picker input parsing
```

Commands take injected `add` / `remove` / `addRemote` functions, so tests never touch the network.

## Tests

```bash
npm test            # fast, offline (fake `npx skills add/remove`)
npm run test:e2e    # real `npx skills`; needs network
```

P0 coverage: hash compatibility with npx, every state, mine/vendored source lookup, install (both folders, unknown skill), pull (update / new listing / keep local edits / dry-run), push (mine / vendored skipped / dry-run / conflict), vendored refresh (remove→add order from lock source, dry-run, mine/unknown rejected, add-failure restore hint).
