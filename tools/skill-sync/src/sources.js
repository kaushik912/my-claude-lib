import fs from 'node:fs';
import path from 'node:path';

function skillNames(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir, { withFileTypes: true })
    .filter((e) => (e.isDirectory() || e.isSymbolicLink()) && fs.existsSync(path.join(dir, e.name, 'SKILL.md')))
    .map((e) => e.name);
}

/** All installable skills: mine (<lib>/skills) win over vendored (<lib>/.agents/skills). */
export function listAvailable(cfg) {
  const byName = new Map();
  for (const name of skillNames(cfg.vendoredSkills)) byName.set(name, { name, origin: 'vendored', dir: cfg.vendoredSkills });
  for (const name of skillNames(cfg.libSkills)) byName.set(name, { name, origin: 'mine', dir: cfg.libSkills });
  return [...byName.values()].sort((a, b) => a.name.localeCompare(b.name));
}

/** Folder that holds the skill, or null. */
export function resolveSource(cfg, name) {
  return listAvailable(cfg).find((s) => s.name === name)?.dir ?? null;
}

/** Group skill names by their source folder: Map<dir, names[]>. */
export function groupBySource(cfg, names) {
  const groups = new Map();
  for (const name of names) {
    const dir = resolveSource(cfg, name);
    groups.set(dir, [...(groups.get(dir) ?? []), name]);
  }
  return groups;
}
