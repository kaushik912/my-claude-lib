import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { hashDir } from '../src/hash.js';
import { resolveConfig } from '../src/config.js';

/** Temp lib (skills/ + .agents/skills) and an empty project. */
export function tmpWorld() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'skill-sync-'));
  const cfg = resolveConfig({ flags: { lib: path.join(root, 'lib') }, toolDir: root });
  const projectDir = path.join(root, 'project');
  for (const d of [cfg.libSkills, cfg.vendoredSkills, path.join(projectDir, '.agents', 'skills')]) {
    fs.mkdirSync(d, { recursive: true });
  }
  return { root, cfg, projectDir, cleanup: () => fs.rmSync(root, { recursive: true, force: true }) };
}

export function writeSkill(skillsDir, name, files) {
  const dir = path.join(skillsDir, name);
  fs.rmSync(dir, { recursive: true, force: true });
  for (const [rel, content] of Object.entries(typeof files === 'string' ? { 'SKILL.md': files } : files)) {
    fs.mkdirSync(path.dirname(path.join(dir, rel)), { recursive: true });
    fs.writeFileSync(path.join(dir, rel), content);
  }
}

/** Record `skill` in <cwd>/skills-lock.json like the CLI does. */
export function writeLockEntry(cwd, name, entry) {
  const lockFile = path.join(cwd, 'skills-lock.json');
  const lock = fs.existsSync(lockFile) ? JSON.parse(fs.readFileSync(lockFile, 'utf8')) : { version: 1, skills: {} };
  lock.skills[name] = entry;
  fs.writeFileSync(lockFile, JSON.stringify(lock, null, 2));
}

/**
 * Fake of `npx skills add`: copies skills into <cwd>/.agents/skills and records
 * computedHash in <cwd>/skills-lock.json, like the real CLI. Records calls.
 */
export function fakeAdd() {
  const calls = [];
  const add = (sourceDir, names, cwd) => {
    calls.push({ sourceDir, names: [...names], cwd });
    for (const n of names) {
      const dest = path.join(cwd, '.agents', 'skills', n);
      fs.rmSync(dest, { recursive: true, force: true });
      fs.cpSync(path.join(sourceDir, n), dest, { recursive: true });
      writeLockEntry(cwd, n, { source: sourceDir, sourceType: 'local', computedHash: hashDir(path.join(sourceDir, n)) });
    }
  };
  return { add, calls };
}
