import fs from 'node:fs';
import path from 'node:path';

const CONTEXT = 3;
const MAX_CELLS = 4_000_000;

/** Unified-style line diff of two strings ('' = absent). Returns '' when equal. */
export function diffText(oldText, newText) {
  const a = oldText === '' ? [] : oldText.split('\n');
  const b = newText === '' ? [] : newText.split('\n');
  if (a.length * b.length > MAX_CELLS) return `(too large to diff: ${a.length} -> ${b.length} lines)`;
  const ops = editScript(a, b);
  if (ops.every((o) => o.t === ' ')) return '';
  return hunks(ops).join('\n');
}

/** LCS-based edit script: [{ t: ' '|'-'|'+', s }]. */
function editScript(a, b) {
  const lcs = Array.from({ length: a.length + 1 }, () => new Uint32Array(b.length + 1));
  for (let i = a.length - 1; i >= 0; i--) {
    for (let j = b.length - 1; j >= 0; j--) {
      lcs[i][j] = a[i] === b[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
    }
  }
  const ops = [];
  let i = 0;
  let j = 0;
  while (i < a.length || j < b.length) {
    if (i < a.length && j < b.length && a[i] === b[j]) ops.push({ t: ' ', s: a[i++] }), j++;
    else if (i < a.length && (j === b.length || lcs[i + 1][j] >= lcs[i][j + 1])) ops.push({ t: '-', s: a[i++] });
    else ops.push({ t: '+', s: b[j++] });
  }
  return ops;
}

function hunks(ops) {
  const keep = ops.map((o, k) => o.t !== ' ' || ops.slice(Math.max(0, k - CONTEXT), k + CONTEXT + 1).some((x) => x.t !== ' '));
  const out = [];
  let inHunk = false;
  ops.forEach((o, k) => {
    if (!keep[k]) return void (inHunk = false);
    if (!inHunk) out.push('@@');
    inHunk = true;
    out.push(`${o.t}${o.s}`);
  });
  return out;
}

function listFiles(p) {
  if (!p || !fs.existsSync(p)) return [];
  if (!fs.statSync(p).isDirectory()) return [''];
  return fs.readdirSync(p, { recursive: true, withFileTypes: true })
    .filter((e) => e.isFile())
    .map((e) => path.relative(p, path.join(e.parentPath, e.name)))
    .sort();
}

/** Text of a file, '' if missing, null if binary. */
function readText(file) {
  if (!file || !fs.existsSync(file)) return '';
  const buf = fs.readFileSync(file);
  return buf.includes(0) ? null : buf.toString('utf8');
}

/**
 * Diff a file or folder `from` -> `to` (either may be missing/null). Returns '' when identical.
 * Format: `--- <rel path>` header per changed file, then its hunks.
 */
export function diffPaths(from, to) {
  const at = (root, rel) => (root ? path.join(root, rel) : null);
  const files = [...new Set([...listFiles(from), ...listFiles(to)])].sort();
  const parts = [];
  for (const rel of files) {
    const [fa, fb] = [at(from, rel), at(to, rel)];
    const [x, y] = [readText(fa), readText(fb)];
    const label = rel || path.basename(to || from);
    const d = x === null || y === null ? binaryDiff(fa, fb) : diffText(x, y);
    if (d) parts.push(`--- ${label}\n${d}`);
  }
  return parts.join('\n');
}

function binaryDiff(fileA, fileB) {
  const [x, y] = [fileA, fileB].map((f) => (f && fs.existsSync(f) ? fs.readFileSync(f) : null));
  return x && y && x.equals(y) ? '' : '(binary file differs)';
}
