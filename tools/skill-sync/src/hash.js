import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

function listFiles(root, dir = root) {
  const out = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...listFiles(root, p));
    else out.push(p);
  }
  return out;
}

/** SHA-256 of one file's content, or null if it doesn't exist. */
export function hashFile(file) {
  if (!fs.existsSync(file)) return null;
  return createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

/**
 * SHA-256 over all files in a skill folder (sorted relative path + content).
 * Matches `computedHash` written by `npx skills` in skills-lock.json.
 * Returns null if the folder doesn't exist.
 */
export function hashDir(dir) {
  if (!fs.existsSync(dir)) return null;
  const files = listFiles(dir)
    .map((f) => ({ abs: f, rel: path.relative(dir, f).split(path.sep).join('/') }))
    .sort((a, b) => a.rel.localeCompare(b.rel));
  const h = createHash('sha256');
  for (const f of files) {
    h.update(f.rel);
    h.update(fs.readFileSync(f.abs));
  }
  return h.digest('hex');
}
