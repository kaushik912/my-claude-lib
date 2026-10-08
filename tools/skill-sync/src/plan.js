import path from 'node:path';
import { hashDir } from './hash.js';
import { readLockSkills } from './lock.js';

/**
 * Three-way state of one installed skill.
 *   src   = hash of the source copy now
 *   lock  = hash recorded in skills-lock.json at install time
 *   local = hash of the installed copy now
 */
export function classify({ src, lock, local }) {
  if (src == null) return 'missing-upstream';
  if (local == null) return 'missing-local';
  const upstream = src !== lock;
  const localEdit = local !== lock;
  if (!upstream && !localEdit) return 'in-sync';
  if (upstream && !localEdit) return 'upstream';
  if (!upstream && localEdit) return 'local';
  return src === local ? 'converged' : 'conflict';
}

/**
 * State of every skill recorded in the project's lock.
 * `sourceDirOf(name)` returns the folder holding the source copy (or null).
 * `names` (optional) limits the skills considered.
 */
export function plan({ sourceDirOf, projectDir, projectSkillsDir, names }) {
  const lockSkills = readLockSkills(projectDir);
  return Object.entries(lockSkills)
    .filter(([name]) => !names?.length || names.includes(name))
    .map(([name, entry]) => {
      const dir = sourceDirOf(name);
      return {
        name,
        sourceDir: dir,
        state: classify({
          src: dir ? hashDir(path.join(dir, name)) : null,
          lock: entry.computedHash,
          local: hashDir(path.join(projectSkillsDir, name)),
        }),
      };
    });
}
