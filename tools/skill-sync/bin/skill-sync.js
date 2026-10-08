#!/usr/bin/env node
import path from 'node:path';
import readline from 'node:readline/promises';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { resolveConfig } from '../src/config.js';
import { bundleSkills } from '../src/bundles.js';
import { refreshVendored, vendoredSkills } from '../src/commands.js';
import { npxAdd, npxAddRemote, npxRemove } from '../src/npx.js';
import { dispatch, statusAll } from '../src/ops.js';
import { formatRows } from '../src/format.js';
import { DIFF_COMMANDS, withDiff } from '../src/preview.js';
import { parseSelection } from '../src/pick.js';
import { listAvailable } from '../src/sources.js';

const USAGE = `skill-sync              (in a terminal, no args: interactive TUI)
skill-sync <command> [skills...] [options]

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

options: --dry-run  --force  --adopt  --kind <kind>  --all-kinds (status only)  --bundle <name> (install only, repeatable)  --diff (with --dry-run: pull/push/remove)  --lib <dir>
env:     SKILL_SYNC_LIB`;

const COMMANDS = ['install', 'pull', 'push', 'status', 'remove'];

const { values: flags, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    'dry-run': { type: 'boolean' },
    force: { type: 'boolean' },
    adopt: { type: 'boolean' },
    kind: { type: 'string' },
    'all-kinds': { type: 'boolean' },
    bundle: { type: 'string', multiple: true },
    diff: { type: 'boolean' },
    lib: { type: 'string' },
    help: { type: 'boolean', short: 'h' },
  },
});
const [command, ...names] = positionals;

function print(rows) {
  console.log(formatRows(rows));
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
  if (flags.help) return console.log(USAGE);
  const interactive = !command && process.stdin.isTTY && process.stdout.isTTY;
  if (!command && !interactive) return console.log(USAGE);
  const toolDir = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
  const cfg = resolveConfig({ flags, env: process.env, toolDir });
  const projectDir = process.cwd();
  const opts = { cfg, projectDir, names, dryRun: flags['dry-run'], force: flags.force, add: npxAdd, remove: npxRemove, addRemote: npxAddRemote };

  if (interactive) {
    const [{ runTui }, { clackUi }] = await Promise.all([import('../src/tui.js'), import('../src/ui-clack.js')]);
    return runTui({ base: opts, ui: clackUi });
  }

  if (flags.bundle) {
    if (command !== 'install' || (flags.kind && flags.kind !== 'skills')) throw new Error('--bundle only applies to skills install');
    opts.names = [...new Set([...names, ...bundleSkills(cfg, flags.bundle)])];
  }

  if (flags.diff && (!flags['dry-run'] || !DIFF_COMMANDS.includes(command))) {
    throw new Error(`--diff needs --dry-run and one of: ${DIFF_COMMANDS.join(', ')}`);
  }

  if (flags['all-kinds']) {
    if (command !== 'status') throw new Error('--all-kinds only applies to status');
    return print(statusAll(opts));
  }

  if (command === 'refresh') {
    if (names.length > 1) throw new Error('refresh takes one skill at a time');
    const name = names[0] ?? await pickVendored(cfg);
    return print(refreshVendored({ ...opts, name }));
  }
  if (command === 'install' && !opts.names.length && (!flags.kind || flags.kind === 'skills')) {
    return print(dispatch({ ...opts, command, names: await pickNames(cfg) }));
  }
  if (!COMMANDS.includes(command)) throw new Error(`unknown command: ${command}\n\n${USAGE}`);
  const kind = flags.kind ?? 'skills';
  const rows = dispatch({ ...opts, command, kind, adopt: flags.adopt });
  return print(flags.diff ? withDiff({ rows, ...opts, command, kind }) : rows);
}

main().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
