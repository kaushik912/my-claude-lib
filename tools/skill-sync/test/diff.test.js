import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { afterEach, beforeEach, describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';
import { install, pull, push, uninstall } from '../src/commands.js';
import { diffText } from '../src/diff.js';
import { installFiles, pullFiles } from '../src/files.js';
import { withDiff } from '../src/preview.js';
import { fakeAdd, tmpWorld, writeSkill } from './helpers.js';

const BIN = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'bin', 'skill-sync.js');

describe('diffText', () => {
  it('givenEqualText_whenDiff_thenEmpty', () => {
    assert.equal(diffText('a\nb', 'a\nb'), '');
  });

  it('givenChangedLine_whenDiff_thenMinusPlusWithContext', () => {
    assert.equal(diffText('a\nb\nc', 'a\nB\nc'), '@@\n a\n-b\n+B\n c');
  });

  it('givenAbsentOld_whenDiff_thenAllAdded', () => {
    assert.equal(diffText('', 'x\ny'), '@@\n+x\n+y');
  });

  it('givenFarApartChanges_whenDiff_thenSeparateHunks', () => {
    const lines = Array.from({ length: 20 }, (_, i) => `l${i}`);
    const changed = lines.map((l, i) => (i === 0 || i === 19 ? `${l}!` : l));

    assert.equal(diffText(lines.join('\n'), changed.join('\n')).split('\n').filter((l) => l === '@@').length, 2);
  });
});

describe('withDiff (dry-run previews)', () => {
  let w, f, ctx;
  beforeEach(() => {
    w = tmpWorld();
    f = fakeAdd();
    ctx = { cfg: w.cfg, projectDir: w.projectDir };
    writeSkill(w.cfg.libSkills, 'spec', 'line1\nline2');
  });
  afterEach(() => w.cleanup());

  it('givenLibUpdated_whenPullDryRunDiff_thenShowsProjectToLib', () => {
    install({ ...ctx, names: ['spec'], add: f.add });
    writeSkill(w.cfg.libSkills, 'spec', 'line1\nline2 changed');

    const rows = withDiff({ rows: pull({ ...ctx, dryRun: true, add: f.add }), ...ctx, command: 'pull', kind: 'skills' });

    assert.match(rows.find((r) => r.name === 'spec').diff, /--- SKILL\.md\n@@\n line1\n-line2\n\+line2 changed/);
  });

  it('givenLocalEdit_whenPushDryRunDiff_thenShowsLibToProject', () => {
    install({ ...ctx, names: ['spec'], add: f.add });
    writeSkill(path.join(w.projectDir, '.agents/skills'), 'spec', 'line1\nlocal');

    const rows = withDiff({ rows: push({ ...ctx, dryRun: true }), ...ctx, command: 'push', kind: 'skills' });

    assert.match(rows[0].diff, /-line2\n\+local/);
  });

  it('givenInstalled_whenRemoveDryRunDiff_thenShowsFilesLost', () => {
    install({ ...ctx, names: ['spec'], add: f.add });

    const rows = withDiff({ rows: uninstall({ ...ctx, names: ['spec'], dryRun: true }), ...ctx, command: 'remove', kind: 'skills' });

    assert.match(rows[0].diff, /--- SKILL\.md\n@@\n-line1\n-line2/);
  });

  it('givenUnchanged_whenPullDryRunDiff_thenRowsHaveNoDiff', () => {
    install({ ...ctx, names: ['spec'], add: f.add });

    const rows = withDiff({ rows: pull({ ...ctx, dryRun: true, add: f.add }), ...ctx, command: 'pull', kind: 'skills' });

    assert.ok(rows.every((r) => !r.diff));
  });

  it('givenRuleUpdatedInLib_whenPullDryRunDiff_thenShowsFileDiff', () => {
    const lib = path.join(w.cfg.lib, '.claude/rules/r.md');
    fs.mkdirSync(path.dirname(lib), { recursive: true });
    fs.writeFileSync(lib, 'one');
    installFiles({ ...ctx, kind: 'rules', names: ['r'] });
    fs.writeFileSync(lib, 'two');

    const rows = withDiff({ rows: pullFiles({ ...ctx, kind: 'rules', dryRun: true }), ...ctx, command: 'pull', kind: 'rules' });

    assert.match(rows[0].diff, /-one\n\+two/);
  });
});

describe('--diff flag', () => {
  let w;
  const run = (...args) => spawnSync('node', [BIN, ...args, '--lib', w.cfg.lib], { cwd: w.projectDir, encoding: 'utf8' });
  beforeEach(() => {
    w = tmpWorld();
  });
  afterEach(() => w.cleanup());

  it('givenNoDryRun_whenDiff_thenNonZeroExit', () => {
    const r = run('pull', '--diff');

    assert.equal(r.status, 1);
    assert.match(r.stderr, /--diff needs --dry-run/);
  });

  it('givenRuleLocalEdit_whenPushDryRunDiff_thenPrintsIndentedDiff', () => {
    const lib = path.join(w.cfg.lib, '.claude/rules/r.md');
    fs.mkdirSync(path.dirname(lib), { recursive: true });
    fs.writeFileSync(lib, 'one');
    assert.equal(run('install', '--kind', 'rules', 'r').status, 0);
    fs.writeFileSync(path.join(w.projectDir, '.claude/rules/r.md'), 'edited');

    const r = run('push', '--kind', 'rules', '--dry-run', '--diff');

    assert.equal(r.status, 0, r.stderr);
    assert.match(r.stdout, /would-push\n    --- r\.md\n    @@\n    -one\n    \+edited/);
  });
});
