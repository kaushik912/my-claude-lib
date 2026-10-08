import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const LOCAL_BIN = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'node_modules', '.bin', 'skills');

/**
 * Path of the pinned local `skills` CLI (installed by `npm install` in this tool).
 * No global/npx fallback: one known version keeps hashes and layout predictable.
 * `exists` is injectable for tests.
 */
export function localSkillsBin(exists = (p) => fs.existsSync(p)) {
  if (!exists(LOCAL_BIN)) {
    throw new Error(`skills CLI not installed. Run: (cd ${path.dirname(path.dirname(LOCAL_BIN))} && npm install)  or tools/skill-sync/install.sh`);
  }
  return LOCAL_BIN;
}

function runSkills(args, cwd) {
  const r = spawnSync(localSkillsBin(), args, { cwd, encoding: 'utf8' });
  if (r.status !== 0) {
    throw new Error(`skills ${args[0]} failed (exit ${r.status}):\n${r.stdout}\n${r.stderr}`);
  }
}

/**
 * Install (or re-install, overwriting) skills via the `skills` CLI.
 * Layout, same for registry and projects: real files in .agents/skills (agent-agnostic),
 * .claude/skills symlinked to them. claude-code alone gets a plain copy in .claude/skills;
 * adding a universal agent (github-copilot) makes the CLI use .agents/skills as canonical.
 * Pull re-runs `add` (re-install overwrites). Injected into commands so tests can fake it.
 */
export function npxAdd(sourceDir, names, cwd) {
  runSkills(['add', sourceDir, '--skill', ...names, '-a', 'claude-code', 'github-copilot', '-y'], cwd);
}

/** Vendor refresh, step 1: drop the skill (also removes its lock entry). */
export function npxRemove(name, cwd) {
  runSkills(['remove', name, '-y'], cwd);
}

/** Vendor refresh, step 2: re-add from the upstream source (e.g. `JuliusBrussee/caveman`). */
export function npxAddRemote(source, name, cwd) {
  runSkills(['add', source, '--skill', name, '-y'], cwd);
}
