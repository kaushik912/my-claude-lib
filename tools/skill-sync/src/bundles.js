import fs from 'node:fs';
import path from 'node:path';

/** Bundles from <lib>/.claude-plugin/marketplace.json as [{ name, version, skills: [name] }]. */
export function readBundles(cfg) {
  const file = path.join(cfg.lib, '.claude-plugin', 'marketplace.json');
  if (!fs.existsSync(file)) return [];
  const { plugins = [] } = JSON.parse(fs.readFileSync(file, 'utf8'));
  return plugins.map((p) => ({ name: p.name, version: p.version, skills: (p.skills ?? []).map((s) => path.basename(s)) }));
}

/** Skill names of the given bundles (deduped, in order). Throws on an unknown bundle. */
export function bundleSkills(cfg, bundleNames) {
  const bundles = readBundles(cfg);
  const unknown = bundleNames.filter((n) => !bundles.some((b) => b.name === n));
  if (unknown.length) throw new Error(`unknown bundle: ${unknown.join(', ')} (available: ${bundles.map((b) => b.name).join(', ') || 'none'})`);
  return [...new Set(bundleNames.flatMap((n) => bundles.find((b) => b.name === n).skills))];
}
