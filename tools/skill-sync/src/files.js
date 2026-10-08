import fs from 'node:fs';
import path from 'node:path';
import { hashFile } from './hash.js';
import { classify } from './plan.js';

/**
 * Single-file kinds (commands, agents, rules): <lib>/.claude/<kind>/<name>.md
 * copied to <project>/.claude/<kind>/<name>.md and tracked in
 * <project>/.claude/claude-lib-lock.json as { files: { "<kind>/<name>": { hash } } }.
 */
export const FILE_KINDS = ['commands', 'agents', 'rules'];

const UPDATABLE = new Set(['upstream', 'converged']);

function assertKind(kind) {
  if (!FILE_KINDS.includes(kind)) throw new Error(`unknown kind: ${kind} (one of ${FILE_KINDS.join(', ')})`);
}

const libPath = (cfg, kind, name) => path.join(cfg.lib, '.claude', kind, `${name}.md`);
const projPath = (projectDir, kind, name) => path.join(projectDir, '.claude', kind, `${name}.md`);
const lockPath = (projectDir) => path.join(projectDir, '.claude', 'claude-lib-lock.json');

function readLock(projectDir) {
  const file = lockPath(projectDir);
  return fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')).files ?? {} : {};
}

function writeLock(projectDir, files) {
  fs.mkdirSync(path.dirname(lockPath(projectDir)), { recursive: true });
  fs.writeFileSync(lockPath(projectDir), JSON.stringify({ version: 1, files }, null, 2) + '\n');
}

function copyFile(from, to) {
  fs.mkdirSync(path.dirname(to), { recursive: true });
  fs.copyFileSync(from, to);
}

/** Names of the kind recorded in the project's lock (filtered by `names` if given). */
function trackedNames(projectDir, kind, names) {
  return Object.keys(readLock(projectDir))
    .filter((k) => k.startsWith(`${kind}/`))
    .map((k) => k.slice(kind.length + 1))
    .filter((n) => !names?.length || names.includes(n));
}

function libNames(cfg, kind) {
  const dir = path.join(cfg.lib, '.claude', kind);
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((f) => f.endsWith('.md')).map((f) => f.slice(0, -3)).sort();
}

function planFiles({ cfg, projectDir, kind, names }) {
  const lock = readLock(projectDir);
  return trackedNames(projectDir, kind, names).map((name) => ({
    name,
    state: classify({
      src: hashFile(libPath(cfg, kind, name)),
      lock: lock[`${kind}/${name}`].hash,
      local: hashFile(projPath(projectDir, kind, name)),
    }),
  }));
}

function newRows({ cfg, projectDir, kind, names }) {
  const tracked = new Set(trackedNames(projectDir, kind));
  return libNames(cfg, kind)
    .filter((n) => !tracked.has(n) && (!names?.length || names.includes(n)))
    .map((name) => ({ name, state: 'new', action: `not installed; skill-sync install --kind ${kind} ${name}` }));
}

/** Files in the project's .claude/<kind>/ that have no lock entry (made in the project). */
function untrackedNames(projectDir, kind) {
  const dir = path.join(projectDir, '.claude', kind);
  if (!fs.existsSync(dir)) return [];
  const tracked = new Set(trackedNames(projectDir, kind));
  return fs.readdirSync(dir).filter((f) => f.endsWith('.md')).map((f) => f.slice(0, -3)).filter((n) => !tracked.has(n));
}

function untrackedRows({ cfg, projectDir, kind, names }) {
  return untrackedNames(projectDir, kind)
    .filter((n) => !names?.length || names.includes(n))
    .map((name) => ({
      name,
      state: 'untracked',
      action: fs.existsSync(libPath(cfg, kind, name))
        ? `project only, but name exists in lib; rename, or push --adopt --kind ${kind} ${name} --force`
        : `project only; skill-sync push --adopt --kind ${kind} ${name}`,
    }));
}

/** Per-item state of the project vs lib, plus untracked and not-installed items. */
export function statusFiles({ cfg, projectDir, kind, names }) {
  assertKind(kind);
  const untracked = untrackedRows({ cfg, projectDir, kind, names });
  const clash = new Set(untracked.map((r) => r.name));
  const fresh = newRows({ cfg, projectDir, kind, names }).filter((r) => !clash.has(r.name));
  return [...planFiles({ cfg, projectDir, kind, names }), ...untracked, ...fresh];
}

/** lib -> project, first install. Refuses to overwrite an existing file unless `force`. */
export function installFiles({ cfg, projectDir, kind, names, force }) {
  assertKind(kind);
  if (!names?.length) throw new Error(`no items given (available: ${libNames(cfg, kind).join(', ') || 'none'})`);
  const unknown = names.filter((n) => !fs.existsSync(libPath(cfg, kind, n)));
  if (unknown.length) throw new Error(`not in lib: ${unknown.join(', ')}`);
  const existing = names.filter((n) => fs.existsSync(projPath(projectDir, kind, n)));
  if (existing.length && !force) throw new Error(`exists in project: ${existing.join(', ')} (pull, or --force to overwrite)`);
  const lock = readLock(projectDir);
  for (const name of names) {
    copyFile(libPath(cfg, kind, name), projPath(projectDir, kind, name));
    lock[`${kind}/${name}`] = { hash: hashFile(libPath(cfg, kind, name)) };
  }
  writeLock(projectDir, lock);
  return names.map((name) => ({ name, state: 'new', action: 'installed' }));
}

/** lib -> project. Applies upstream changes; never overwrites local edits unless `force` on a conflict. */
export function pullFiles({ cfg, projectDir, kind, names, dryRun, force }) {
  assertKind(kind);
  const lock = readLock(projectDir);
  const rows = planFiles({ cfg, projectDir, kind, names }).map(({ name, state }) => {
    const apply = UPDATABLE.has(state) || (force && state === 'conflict');
    if (apply && !dryRun) {
      copyFile(libPath(cfg, kind, name), projPath(projectDir, kind, name));
      lock[`${kind}/${name}`] = { hash: hashFile(libPath(cfg, kind, name)) };
    }
    return { name, state, action: apply ? (dryRun ? 'would-update' : 'updated') : 'skipped' };
  });
  if (!dryRun) writeLock(projectDir, lock);
  return [...rows, ...newRows({ cfg, projectDir, kind, names })];
}

/** project -> lib for locally edited items. Writes lib, never commits. */
export function pushFiles({ cfg, projectDir, kind, names, dryRun, force }) {
  assertKind(kind);
  const lock = readLock(projectDir);
  const rows = [];
  for (const name of trackedNames(projectDir, kind, names)) {
    const local = hashFile(projPath(projectDir, kind, name));
    const locked = lock[`${kind}/${name}`].hash;
    if (local == null || local === locked) continue; // nothing to push
    const libHash = hashFile(libPath(cfg, kind, name));
    if (libHash == null) rows.push({ name, state: 'local', action: 'skipped (not in lib)' });
    else if (libHash === local) rows.push({ name, state: 'in-sync', action: 'skipped' });
    else if (libHash !== locked && !force) rows.push({ name, state: 'conflict', action: 'skipped (lib changed since install; pull first or --force)' });
    else {
      if (!dryRun) copyFile(projPath(projectDir, kind, name), libPath(cfg, kind, name));
      rows.push({ name, state: 'local', action: dryRun ? 'would-push' : 'pushed' });
    }
  }
  return rows;
}

/** project -> lib for files made in the project (no lock entry); tracks them afterwards. */
export function adoptFiles({ cfg, projectDir, kind, names, dryRun, force }) {
  assertKind(kind);
  if (!names?.length) throw new Error('no items given');
  const untracked = new Set(untrackedNames(projectDir, kind));
  const notUntracked = names.filter((n) => !untracked.has(n));
  if (notUntracked.length) throw new Error(`not untracked in project: ${notUntracked.join(', ')}`);
  const clash = names.filter((n) => fs.existsSync(libPath(cfg, kind, n)));
  if (clash.length && !force) throw new Error(`exists in lib: ${clash.join(', ')} (--force to overwrite)`);
  const lock = readLock(projectDir);
  for (const name of names) {
    if (dryRun) continue;
    copyFile(projPath(projectDir, kind, name), libPath(cfg, kind, name));
    lock[`${kind}/${name}`] = { hash: hashFile(libPath(cfg, kind, name)) };
  }
  if (!dryRun) writeLock(projectDir, lock);
  return names.map((name) => ({ name, state: 'untracked', action: dryRun ? 'would-adopt' : 'adopted' }));
}

/** Delete installed items (file + lock entry). */
export function removeFiles({ projectDir, kind, names, dryRun }) {
  assertKind(kind);
  if (!names?.length) throw new Error('no items given');
  const tracked = new Set(trackedNames(projectDir, kind));
  const unknown = names.filter((n) => !tracked.has(n));
  if (unknown.length) throw new Error(`not installed in project: ${unknown.join(', ')}`);
  const lock = readLock(projectDir);
  for (const name of names) {
    if (dryRun) continue;
    fs.rmSync(projPath(projectDir, kind, name), { force: true });
    delete lock[`${kind}/${name}`];
  }
  if (!dryRun) writeLock(projectDir, lock);
  return names.map((name) => ({ name, state: 'installed', action: dryRun ? 'would-remove' : 'removed' }));
}
