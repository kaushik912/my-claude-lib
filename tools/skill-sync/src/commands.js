import fs from 'node:fs';
import path from 'node:path';
import { hashDir } from './hash.js';
import { readLockSkills } from './lock.js';
import { plan } from './plan.js';
import { projectSkillsDir } from './config.js';
import { groupBySource, listAvailable, resolveSource } from './sources.js';

const UPDATABLE = new Set(['upstream', 'converged']);

function planProject({ cfg, projectDir, names }) {
  return plan({
    sourceDirOf: (name) => resolveSource(cfg, name),
    projectDir,
    projectSkillsDir: projectSkillsDir(projectDir),
    names,
  });
}

/** Skills available in lib but not installed in the project. */
function newSkillRows({ cfg, projectDir, names }) {
  const installed = new Set(Object.keys(readLockSkills(projectDir)));
  return listAvailable(cfg)
    .filter((s) => !installed.has(s.name) && (!names?.length || names.includes(s.name)))
    .map((s) => ({ name: s.name, state: 'new', action: `not installed (${s.origin}); skill-sync install ${s.name}` }));
}

/** Skill folders in the project that have no lock entry (made in the project). */
function untrackedSkillNames(projectDir) {
  const dir = projectSkillsDir(projectDir);
  if (!fs.existsSync(dir)) return [];
  const tracked = new Set(Object.keys(readLockSkills(projectDir)));
  return fs
    .readdirSync(dir, { withFileTypes: true })
    .filter((e) => e.isDirectory() && !tracked.has(e.name) && fs.existsSync(path.join(dir, e.name, 'SKILL.md')))
    .map((e) => e.name);
}

function untrackedSkillRows({ cfg, projectDir, names }) {
  return untrackedSkillNames(projectDir)
    .filter((n) => !names?.length || names.includes(n))
    .map((name) => ({
      name,
      state: 'untracked',
      action: resolveSource(cfg, name)
        ? `project only, but name exists in lib; rename, or push --adopt ${name} --force`
        : `project only; skill-sync push --adopt ${name}`,
    }));
}

/** Install skills from their source folders (one `add` call per folder). */
function addGrouped(cfg, names, projectDir, add) {
  for (const [dir, group] of groupBySource(cfg, names)) add(dir, group, projectDir);
}

/** Per-skill state of the project vs lib, plus skills not installed yet. */
export function status({ cfg, projectDir, names }) {
  const untracked = untrackedSkillRows({ cfg, projectDir, names });
  const clash = new Set(untracked.map((r) => r.name));
  const fresh = newSkillRows({ cfg, projectDir, names }).filter((r) => !clash.has(r.name));
  return [...planProject({ cfg, projectDir, names }), ...untracked, ...fresh];
}

/**
 * lib -> project. Updates installed skills whose source changed; never overwrites
 * local edits unless `force`. Also lists skills in lib that aren't installed.
 */
export function pull({ cfg, projectDir, dryRun, force, names, add }) {
  const rows = planProject({ cfg, projectDir, names }).map(({ name, state }) => {
    const apply = UPDATABLE.has(state) || (force && state === 'conflict');
    return { name, state, action: apply ? (dryRun ? 'would-update' : 'updated') : 'skipped' };
  });
  const toApply = rows.filter((r) => r.action === 'updated').map((r) => r.name);
  if (toApply.length) addGrouped(cfg, toApply, projectDir, add);
  return [...rows, ...newSkillRows({ cfg, projectDir, names })];
}

/** lib -> project, first install. */
export function install({ cfg, projectDir, names, add }) {
  if (!names.length) throw new Error('no skills given');
  const available = new Set(listAvailable(cfg).map((s) => s.name));
  const unknown = names.filter((n) => !available.has(n));
  if (unknown.length) throw new Error(`not in lib: ${unknown.join(', ')}`);
  addGrouped(cfg, names, projectDir, add);
  return names.map((name) => ({ name, state: 'new', action: 'installed' }));
}

/** Uninstall skills from the project (files, symlink and lock entry, via `skills remove`). */
export function uninstall({ projectDir, names, dryRun, remove }) {
  if (!names.length) throw new Error('no skills given');
  const installed = new Set(Object.keys(readLockSkills(projectDir)));
  const unknown = names.filter((n) => !installed.has(n));
  if (unknown.length) throw new Error(`not installed in project: ${unknown.join(', ')}`);
  return names.map((name) => {
    if (!dryRun) remove(name, projectDir);
    return { name, state: 'installed', action: dryRun ? 'would-remove' : 'removed' };
  });
}

/**
 * project -> lib. Only skills that exist in <lib>/skills (i.e. mine) are pushed;
 * vendored skills live in .agents/skills, so they are skipped. lib is written, never committed.
 */
export function push({ cfg, projectDir, dryRun, force, names }) {
  const lock = readLockSkills(projectDir);
  const rows = [];
  for (const [name, entry] of Object.entries(lock)) {
    if (names?.length && !names.includes(name)) continue;
    const srcDir = path.join(projectSkillsDir(projectDir), name);
    const libDir = path.join(cfg.libSkills, name);
    const local = hashDir(srcDir);
    if (local === entry.computedHash) continue; // unchanged locally, nothing to push
    if (!fs.existsSync(libDir)) {
      rows.push({ name, state: 'local', action: 'skipped (not in lib/skills)' });
      continue;
    }
    const libHash = hashDir(libDir);
    if (libHash === local) {
      rows.push({ name, state: 'in-sync', action: 'skipped' });
      continue;
    }
    if (libHash !== entry.computedHash && !force) {
      rows.push({ name, state: 'conflict', action: 'skipped (lib changed since install; pull first or --force)' });
      continue;
    }
    if (!dryRun) {
      fs.rmSync(libDir, { recursive: true, force: true });
      fs.cpSync(srcDir, libDir, { recursive: true });
    }
    rows.push({ name, state: 'local', action: dryRun ? 'would-push' : 'pushed' });
  }
  return rows;
}

/**
 * project -> lib for skills made in the project (no lock entry): copy into <lib>/skills,
 * then `add` from lib so the project tracks it. Refuses names already in lib unless `force`.
 */
export function adoptSkills({ cfg, projectDir, names, dryRun, force, add }) {
  if (!names?.length) throw new Error('no items given');
  const untracked = new Set(untrackedSkillNames(projectDir));
  const notUntracked = names.filter((n) => !untracked.has(n));
  if (notUntracked.length) throw new Error(`not untracked in project: ${notUntracked.join(', ')}`);
  const clash = names.filter((n) => resolveSource(cfg, n));
  if (clash.length && !force) throw new Error(`exists in lib: ${clash.join(', ')} (--force to overwrite)`);
  return names.map((name) => {
    if (!dryRun) {
      const libDir = path.join(cfg.libSkills, name);
      fs.rmSync(libDir, { recursive: true, force: true });
      fs.cpSync(path.join(projectSkillsDir(projectDir), name), libDir, { recursive: true });
      add(cfg.libSkills, [name], projectDir);
    }
    return { name, state: 'untracked', action: dryRun ? 'would-adopt' : 'adopted (add it to a marketplace.json bundle)' };
  });
}

/** Skill names in lib's lock that came from upstream (not local paths). */
export function vendoredSkills(cfg) {
  return Object.entries(readLockSkills(cfg.registry))
    .filter(([, e]) => e.sourceType !== 'local')
    .map(([name, e]) => ({ name, source: e.source }));
}

/**
 * Refresh ONE vendored skill: remove, then re-add from its upstream source.
 * Source is read from the lock first (remove deletes the entry).
 * `remove(name, cwd)` / `addRemote(source, name, cwd)` are injected so tests can fake them.
 */
export function refreshVendored({ cfg, name, dryRun, remove, addRemote }) {
  const entry = vendoredSkills(cfg).find((s) => s.name === name);
  if (!entry) throw new Error(`not a vendored skill in lib: ${name}`);
  const { source } = entry;
  if (dryRun) {
    return [{ name, state: 'vendored', action: `would run: skills remove ${name} -y; skills add ${source} --skill ${name} -y` }];
  }
  const before = hashDir(path.join(cfg.vendoredSkills, name));
  remove(name, cfg.registry);
  try {
    addRemote(source, name, cfg.registry);
  } catch (e) {
    throw new Error(`${name} removed but re-add failed. Restore with: skills add ${source} --skill ${name} -y\n${e.message}`);
  }
  const changed = hashDir(path.join(cfg.vendoredSkills, name)) !== before;
  return [{ name, state: changed ? 'upstream' : 'in-sync', action: changed ? 'updated' : 'unchanged' }];
}
