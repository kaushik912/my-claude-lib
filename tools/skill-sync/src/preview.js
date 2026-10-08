import path from 'node:path';
import { projectSkillsDir } from './config.js';
import { diffPaths } from './diff.js';
import { resolveSource } from './sources.js';

export const DIFF_COMMANDS = ['pull', 'push', 'remove'];

/** [oldPath, newPath] a dry-run row would change, or null. Missing paths diff as empty. */
function sides({ cfg, projectDir, command, kind, name }) {
  const skills = kind === 'skills';
  const proj = skills ? path.join(projectSkillsDir(projectDir), name) : path.join(projectDir, '.claude', kind, `${name}.md`);
  const lib = skills ? path.join(cfg.libSkills, name) : path.join(cfg.lib, '.claude', kind, `${name}.md`);
  if (command === 'remove') return [proj, null];
  if (command === 'push') return [lib, proj]; // push and push --adopt both write project -> lib
  if (!skills) return [proj, lib]; // pull
  const dir = resolveSource(cfg, name);
  return dir && [proj, path.join(dir, name)];
}

/** Add a `diff` string to dry-run rows that would change something. */
export function withDiff({ rows, ...ctx }) {
  return rows.map((r) => {
    if (!r.action?.startsWith('would-')) return r;
    const s = sides({ ...ctx, name: r.name });
    return s ? { ...r, diff: diffPaths(...s) } : r;
  });
}
