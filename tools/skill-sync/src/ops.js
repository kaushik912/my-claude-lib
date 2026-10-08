import { adoptSkills, install, pull, push, status, uninstall } from './commands.js';
import { adoptFiles, FILE_KINDS, installFiles, pullFiles, pushFiles, removeFiles, statusFiles } from './files.js';

export const KINDS = ['skills', ...FILE_KINDS];

const skillOps = { install, pull, push, status, remove: uninstall };
const fileOps = { install: installFiles, pull: pullFiles, push: pushFiles, status: statusFiles, remove: removeFiles };

/** Run a project command for one kind. The single entry point for both the CLI and any UI. */
export function dispatch({ command, kind = 'skills', adopt, ...opts }) {
  if (!KINDS.includes(kind)) throw new Error(`unknown kind: ${kind} (one of ${KINDS.join(', ')})`);
  if (!(command in skillOps)) throw new Error(`unknown command: ${command}`);
  if (kind === 'skills') return (adopt && command === 'push' ? adoptSkills : skillOps[command])(opts);
  const fn = adopt && command === 'push' ? adoptFiles : fileOps[command];
  if (!fn) throw new Error(`${command} does not support --kind ${kind}`);
  return fn({ ...opts, kind });
}

/** Status rows for every kind, each tagged with its `kind`. */
export function statusAll(opts) {
  return KINDS.flatMap((kind) => dispatch({ ...opts, command: 'status', kind }).map((r) => ({ ...r, kind })));
}
