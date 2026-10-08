#!/usr/bin/env node
import path from 'node:path';
import readline from 'node:readline/promises';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { resolveConfig } from '../src/config.js';
import { adoptSkills, install, pull, push, refreshVendored, status, uninstall, vendoredSkills } from '../src/commands.js';
import { adoptFiles, installFiles, pullFiles, pushFiles, removeFiles, statusFiles } from '../src/files.js';
import { npxAdd, npxAddRemote, npxRemove } from '../src/npx.js';
import { parseSelection } from '../src/pick.js';
import { listAvailable } from '../src/sources.js';

const USAGE = `skill-sync <command> [skills...] [options]

project commands (run in the project dir):
  install   lib -> project   (no names = interactive picker)
  pull      lib -> project   (update installed skills; lists new ones)
  push      project -> lib   (only skills in lib/skills; uncommitted)
  push --adopt <names>  copy skills made in the project into lib/skills and track them
  status    project vs lib   (also lists untracked = made in project, and new)
  remove    uninstall skills from the project (files, symlink, lock entry)

lib owner command:
  refresh   re-fetch ONE vendored skill from upstream (remove + add; no name = interactive picker)

--kind commands|agents|rules (install/pull/push/status/remove): plain-file copies of
  <lib>/.claude/<kind>/<name>.md into <project>/.claude/<kind>/, names required, no picker.

options: --dry-run  --force  --adopt  --kind <kind>  --lib <dir>
env:     SKILL_SYNC_LIB`;

const { values: flags, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    'dry-run': { type: 'boolean' },
    force: { type: 'boolean' },
    adopt: { type: 'boolean' },
    kind: { type: 'string' },
    lib: { type: 'string' },
    help: { type: 'boolean', short: 'h' },
  },
});
const [command, ...names] = positionals;

function print(rows) {
  if (!rows.length) return console.log('nothing to do');
  const w = Math.max(...rows.map((r) => r.name.length));
  for (const r of rows) console.log(`${r.name.padEnd(w)}  ${r.state.padEnd(16)}  ${r.action ?? ''}`.trimEnd());
}

async function pickNames(cfg) {
  const items = listAvailable(cfg);
  if (!items.length) throw new Error(`no skills in lib: ${cfg.libSkills}`);
  items.forEach((s, i) => console.log(`${String(i + 1).padStart(3)}) ${s.name}  (${s.origin})`));
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  try {
    return parseSelection(await rl.question('pick (numbers or "all"): '), items.map((s) => s.name));
  } finally {
    rl.close();
  }
}

async function pickVendored(cfg) {
  const items = vendoredSkills(cfg);
  if (!items.length) throw new Error(`no vendored skills in lib: ${cfg.registry}`);
  items.forEach((s, i) => console.log(`${String(i + 1).padStart(3)}) ${s.name}  (${s.source})`));
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  try {
    const [name, ...rest] = parseSelection(await rl.question('pick one (number): '), items.map((s) => s.name));
    if (rest.length) throw new Error('pick exactly one skill');
    return name;
  } finally {
    rl.close();
  }
}

async function main() {
  if (flags.help || !command) return console.log(USAGE);
  const toolDir = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
  const cfg = resolveConfig({ flags, env: process.env, toolDir });
  const projectDir = process.cwd();
  const opts = { cfg, projectDir, names, dryRun: flags['dry-run'], force: flags.force, add: npxAdd, remove: npxRemove, addRemote: npxAddRemote };

  if (flags.kind && flags.kind !== 'skills') {
    const fileOps = { install: installFiles, pull: pullFiles, push: flags.adopt ? adoptFiles : pushFiles, status: statusFiles, remove: removeFiles };
    if (!fileOps[command]) throw new Error(`${command} does not support --kind ${flags.kind}`);
    return print(fileOps[command]({ ...opts, kind: flags.kind }));
  }

  switch (command) {
    case 'refresh': {
      if (names.length > 1) throw new Error('refresh takes one skill at a time');
      const name = names[0] ?? await pickVendored(cfg);
      return print(refreshVendored({ ...opts, name }));
    }
    case 'pull': return print(pull(opts));
    case 'push': return print(flags.adopt ? adoptSkills(opts) : push(opts));
    case 'status': return print(status(opts));
    case 'remove': return print(uninstall(opts));
    case 'install': {
      const chosen = names.length ? names : await pickNames(cfg);
      return print(install({ ...opts, names: chosen }));
    }
    default: throw new Error(`unknown command: ${command}\n\n${USAGE}`);
  }
}

main().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
