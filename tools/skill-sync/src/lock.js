import fs from 'node:fs';
import path from 'node:path';

/** Returns the `skills` map of <projectDir>/skills-lock.json, or {} if absent. */
export function readLockSkills(projectDir) {
  const file = path.join(projectDir, 'skills-lock.json');
  if (!fs.existsSync(file)) return {};
  return JSON.parse(fs.readFileSync(file, 'utf8')).skills ?? {};
}
