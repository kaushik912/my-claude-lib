import { bundleSkills, readBundles } from './bundles.js';
import { dispatch, statusAll } from './ops.js';
import { formatRows } from './format.js';
import { withDiff } from './preview.js';

/** Which status states each action can act on. `install` also offers bundles. */
const ACTIONS = {
  install: { states: ['new'], label: 'Install', hint: 'lib -> project' },
  pull: { states: ['upstream', 'converged', 'conflict'], label: 'Pull', hint: 'update from lib' },
  push: { states: ['local', 'untracked'], label: 'Push', hint: 'project -> lib (untracked = adopt)' },
  remove: { states: ['in-sync', 'upstream', 'local', 'converged', 'conflict', 'missing-upstream', 'missing-local'], label: 'Remove', hint: 'uninstall from project' },
};

const key = (r) => `${r.kind}/${r.name}`;

/** Choices for an action: matching status rows, plus bundles (install only). */
export function buildChoices(action, rows, bundles) {
  const items = rows
    .filter((r) => ACTIONS[action].states.includes(r.state))
    .map((r) => ({ value: key(r), label: key(r), hint: r.state }));
  if (action !== 'install') return items;
  const installed = new Set(rows.filter((r) => r.kind === 'skills' && r.state !== 'new').map((r) => r.name));
  const offered = bundles
    .map((b) => ({ ...b, missing: b.skills.filter((s) => !installed.has(s)) }))
    .filter((b) => b.missing.length)
    .map((b) => ({ value: `bundle:${b.name}`, label: `bundle ${b.name}`, hint: `v${b.version}, ${b.missing.length} skill(s) to install` }));
  return [...offered, ...items];
}

/**
 * Selected values -> dispatch calls: [{ kind, names, adopt }].
 * `bundle:<n>` expands to its not-yet-installed skills.
 */
export function buildCalls(action, selected, rows, cfg) {
  const installed = new Set(rows.filter((r) => r.kind === 'skills' && r.state !== 'new').map((r) => r.name));
  const byGroup = new Map();
  const add = (kind, name, adopt = false) => {
    const k = `${kind}|${adopt}`;
    const g = byGroup.get(k) ?? { kind, names: [], adopt };
    if (!g.names.includes(name)) g.names.push(name);
    byGroup.set(k, g);
  };
  for (const v of selected) {
    if (v.startsWith('bundle:')) {
      bundleSkills(cfg, [v.slice(7)]).filter((s) => !installed.has(s)).forEach((s) => add('skills', s));
      continue;
    }
    const row = rows.find((r) => key(r) === v);
    const [kind, ...rest] = v.split('/');
    add(kind, rest.join('/'), action === 'push' && row?.state === 'untracked');
  }
  return [...byGroup.values()];
}

/**
 * Prompt-flow TUI over the same `dispatch`/`withDiff` the CLI uses.
 * `base` = { cfg, projectDir, add, remove, addRemote }. `ui` = prompt adapter
 * { intro, outro, note, select, multiselect, confirm } (cancel -> null), injectable for tests.
 */
export async function runTui({ base, ui }) {
  ui.intro('skill-sync');
  const rows = statusAll(base);
  const bundles = readBundles(base.cfg);
  const counts = {};
  for (const r of rows) counts[r.state] = (counts[r.state] ?? 0) + 1;
  ui.note(Object.entries(counts).map(([s, n]) => `${s}: ${n}`).join('\n') || 'nothing in lib or project', 'status');

  const options = Object.entries(ACTIONS)
    .map(([value, a]) => ({ value, label: a.label, hint: `${a.hint} (${buildChoices(value, rows, bundles).length})` }))
    .filter((o) => buildChoices(o.value, rows, bundles).length);
  if (!options.length) return ui.outro('nothing to do');
  const action = await ui.select({ message: 'What do you want to do?', options });
  if (!action) return ui.outro('cancelled');

  const selected = await ui.multiselect({ message: `${ACTIONS[action].label} which?`, options: buildChoices(action, rows, bundles) });
  if (!selected?.length) return ui.outro('cancelled');
  const calls = buildCalls(action, selected, rows, base.cfg);

  const hasConflict = selected.some((v) => rows.find((r) => key(r) === v)?.state === 'conflict');
  const force = action === 'pull' && hasConflict;
  const run = (dryRun) => calls.flatMap(({ kind, names, adopt }) => {
    const ctx = { ...base, command: action, kind, names, adopt, dryRun, force };
    return dryRun ? withDiff({ rows: dispatch(ctx), ...ctx }) : dispatch(ctx);
  });

  if (action !== 'install') ui.note(formatRows(run(true)), 'preview (dry run)');
  const warn = force ? ' Conflicts will be overwritten with the lib version.' : '';
  if (!(await ui.confirm({ message: `Apply ${action} to ${calls.reduce((n, c) => n + c.names.length, 0)} item(s)?${warn}` }))) {
    return ui.outro('cancelled, nothing changed');
  }
  ui.note(formatRows(run(false)), 'result');
  ui.outro('done');
}
