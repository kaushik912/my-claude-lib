import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { afterEach, beforeEach, describe, it } from 'node:test';
import { hashFile } from '../src/hash.js';
import { installFiles, pullFiles, pushFiles, removeFiles, statusFiles } from '../src/files.js';
import { tmpWorld } from './helpers.js';

const libFile = (w, kind, name) => path.join(w.cfg.lib, '.claude', kind, `${name}.md`);
const projFile = (w, kind, name) => path.join(w.projectDir, '.claude', kind, `${name}.md`);
const lockFile = (w) => path.join(w.projectDir, '.claude', 'claude-lib-lock.json');
const write = (file, text) => {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, text);
};
const read = (file) => fs.readFileSync(file, 'utf8');
const stateOf = (rows, name) => rows.find((r) => r.name === name)?.state;
const actionOf = (rows, name) => rows.find((r) => r.name === name)?.action;

describe('file kinds (commands / agents / rules)', () => {
  let w, base;
  beforeEach(() => {
    w = tmpWorld();
    write(libFile(w, 'rules', 'security'), 'sec v1');
    write(libFile(w, 'rules', 'spring'), 'spring v1');
    write(libFile(w, 'commands', 'skills-used'), 'cmd v1');
    base = { cfg: w.cfg, projectDir: w.projectDir, kind: 'rules' };
  });
  afterEach(() => w.cleanup());

  // P0-1
  it('givenLibRules_whenInstall_thenRealCopiesAndLockEntries', () => {
    installFiles({ ...base, names: ['security', 'spring'] });

    for (const n of ['security', 'spring']) {
      assert.ok(!fs.lstatSync(projFile(w, 'rules', n)).isSymbolicLink());
      assert.equal(read(projFile(w, 'rules', n)), read(libFile(w, 'rules', n)));
    }
    const lock = JSON.parse(read(lockFile(w))).files;
    assert.equal(lock['rules/security'].hash, hashFile(libFile(w, 'rules', 'security')));
    assert.equal(Object.keys(lock).length, 2);
  });

  // P0-2
  it('givenUnknownName_whenInstall_thenErrorsAndWritesNothing', () => {
    assert.throws(() => installFiles({ ...base, names: ['security', 'nope'] }), /not in lib: nope/);
    assert.ok(!fs.existsSync(projFile(w, 'rules', 'security')));
    assert.ok(!fs.existsSync(lockFile(w)));
  });

  it('givenNoNames_whenInstall_thenErrors', () => {
    assert.throws(() => installFiles({ ...base, names: [] }), /no items given/);
  });

  it('givenExistingUntrackedFile_whenInstall_thenRefusedUnlessForce', () => {
    write(projFile(w, 'rules', 'security'), 'mine');

    assert.throws(() => installFiles({ ...base, names: ['security'] }), /exists.*--force/);
    assert.equal(read(projFile(w, 'rules', 'security')), 'mine');

    installFiles({ ...base, names: ['security'], force: true });
    assert.equal(read(projFile(w, 'rules', 'security')), 'sec v1');
  });

  // P0-3
  it('givenMixedChanges_whenStatus_thenEveryStateReported', () => {
    installFiles({ ...base, names: ['security', 'spring'] });
    write(libFile(w, 'rules', 'security'), 'sec v2'); // upstream
    write(projFile(w, 'rules', 'spring'), 'spring local'); // local
    write(libFile(w, 'rules', 'testing-style'), 'new'); // new

    const rows = statusFiles(base);

    assert.equal(stateOf(rows, 'security'), 'upstream');
    assert.equal(stateOf(rows, 'spring'), 'local');
    assert.equal(stateOf(rows, 'testing-style'), 'new');
  });

  it('givenBothChanged_whenStatus_thenConflictOrConverged', () => {
    installFiles({ ...base, names: ['security', 'spring'] });
    write(libFile(w, 'rules', 'security'), 'lib edit');
    write(projFile(w, 'rules', 'security'), 'proj edit');
    write(libFile(w, 'rules', 'spring'), 'same edit');
    write(projFile(w, 'rules', 'spring'), 'same edit');

    const rows = statusFiles(base);

    assert.equal(stateOf(rows, 'security'), 'conflict');
    assert.equal(stateOf(rows, 'spring'), 'converged');
  });

  it('givenFilesDeleted_whenStatus_thenMissingStates', () => {
    installFiles({ ...base, names: ['security', 'spring'] });
    fs.rmSync(libFile(w, 'rules', 'security'));
    fs.rmSync(projFile(w, 'rules', 'spring'));

    const rows = statusFiles(base);

    assert.equal(stateOf(rows, 'security'), 'missing-upstream');
    assert.equal(stateOf(rows, 'spring'), 'missing-local');
  });

  // P0-4
  it('givenUpstreamAndLocalEdits_whenPull_thenOnlyUpstreamApplied', () => {
    installFiles({ ...base, names: ['security', 'spring'] });
    write(libFile(w, 'rules', 'security'), 'sec v2');
    write(projFile(w, 'rules', 'spring'), 'spring local');

    const rows = pullFiles(base);

    assert.equal(actionOf(rows, 'security'), 'updated');
    assert.equal(actionOf(rows, 'spring'), 'skipped');
    assert.equal(read(projFile(w, 'rules', 'security')), 'sec v2');
    assert.equal(read(projFile(w, 'rules', 'spring')), 'spring local');
    assert.equal(stateOf(statusFiles(base), 'security'), 'in-sync');
  });

  it('givenUpstreamChange_whenPullDryRun_thenNothingWritten', () => {
    installFiles({ ...base, names: ['security'] });
    write(libFile(w, 'rules', 'security'), 'sec v2');

    const rows = pullFiles({ ...base, dryRun: true });

    assert.equal(actionOf(rows, 'security'), 'would-update');
    assert.equal(read(projFile(w, 'rules', 'security')), 'sec v1');
  });

  it('givenConflict_whenPull_thenSkippedUnlessForce', () => {
    installFiles({ ...base, names: ['security'] });
    write(libFile(w, 'rules', 'security'), 'lib edit');
    write(projFile(w, 'rules', 'security'), 'proj edit');

    assert.equal(actionOf(pullFiles(base), 'security'), 'skipped');
    assert.equal(read(projFile(w, 'rules', 'security')), 'proj edit');

    pullFiles({ ...base, force: true });
    assert.equal(read(projFile(w, 'rules', 'security')), 'lib edit');
  });

  it('givenNewLibFile_whenPull_thenListedNotInstalled', () => {
    installFiles({ ...base, names: ['security'] });

    const rows = pullFiles(base);

    assert.equal(stateOf(rows, 'spring'), 'new');
    assert.ok(!fs.existsSync(projFile(w, 'rules', 'spring')));
  });

  // P0-5
  it('givenLocalEdit_whenPush_thenLibUpdatedAndPullSettlesLock', () => {
    installFiles({ ...base, names: ['spring'] });
    write(projFile(w, 'rules', 'spring'), 'spring improved');

    const rows = pushFiles(base);

    assert.equal(actionOf(rows, 'spring'), 'pushed');
    assert.equal(read(libFile(w, 'rules', 'spring')), 'spring improved');
    assert.equal(stateOf(statusFiles(base), 'spring'), 'converged');
    pullFiles(base);
    assert.equal(stateOf(statusFiles(base), 'spring'), 'in-sync');
  });

  it('givenLibChangedSinceInstall_whenPush_thenConflictSkippedUnlessForce', () => {
    installFiles({ ...base, names: ['spring'] });
    write(projFile(w, 'rules', 'spring'), 'proj edit');
    write(libFile(w, 'rules', 'spring'), 'lib edit');

    assert.match(actionOf(pushFiles(base), 'spring'), /^skipped/);
    assert.equal(read(libFile(w, 'rules', 'spring')), 'lib edit');

    pushFiles({ ...base, force: true });
    assert.equal(read(libFile(w, 'rules', 'spring')), 'proj edit');
  });

  it('givenLocalEdit_whenPushDryRun_thenLibUntouched', () => {
    installFiles({ ...base, names: ['spring'] });
    write(projFile(w, 'rules', 'spring'), 'proj edit');

    const rows = pushFiles({ ...base, dryRun: true });

    assert.equal(actionOf(rows, 'spring'), 'would-push');
    assert.equal(read(libFile(w, 'rules', 'spring')), 'spring v1');
  });

  it('givenLocalEditOfFileGoneFromLib_whenPush_thenSkipped', () => {
    installFiles({ ...base, names: ['spring'] });
    write(projFile(w, 'rules', 'spring'), 'proj edit');
    fs.rmSync(libFile(w, 'rules', 'spring'));

    assert.match(actionOf(pushFiles(base), 'spring'), /^skipped/);
    assert.ok(!fs.existsSync(libFile(w, 'rules', 'spring')));
  });

  // P0-6
  it('givenInstalled_whenRemove_thenFileAndLockEntryGoneOthersKept', () => {
    installFiles({ ...base, names: ['security', 'spring'] });

    removeFiles({ ...base, names: ['spring'] });

    assert.ok(!fs.existsSync(projFile(w, 'rules', 'spring')));
    assert.ok(fs.existsSync(projFile(w, 'rules', 'security')));
    assert.deepEqual(Object.keys(JSON.parse(read(lockFile(w))).files), ['rules/security']);
  });

  it('givenNotInstalled_whenRemove_thenErrors', () => {
    assert.throws(() => removeFiles({ ...base, names: ['spring'] }), /not installed in project: spring/);
  });

  it('givenInstalled_whenRemoveDryRun_thenNothingDeleted', () => {
    installFiles({ ...base, names: ['spring'] });

    const rows = removeFiles({ ...base, names: ['spring'], dryRun: true });

    assert.equal(actionOf(rows, 'spring'), 'would-remove');
    assert.ok(fs.existsSync(projFile(w, 'rules', 'spring')));
  });

  // P0-7
  it('givenSameNameInTwoKinds_whenInstallBoth_thenTrackedIndependently', () => {
    write(libFile(w, 'commands', 'security'), 'cmd sec v1');
    installFiles({ ...base, names: ['security'] });
    installFiles({ ...base, kind: 'commands', names: ['security', 'skills-used'] });
    write(libFile(w, 'commands', 'security'), 'cmd sec v2');

    assert.equal(stateOf(statusFiles(base), 'security'), 'in-sync');
    assert.equal(stateOf(statusFiles({ ...base, kind: 'commands' }), 'security'), 'upstream');
    assert.equal(read(projFile(w, 'rules', 'security')), 'sec v1');
    assert.equal(read(projFile(w, 'commands', 'security')), 'cmd sec v1');
  });

  it('givenUnknownKind_whenInstall_thenErrors', () => {
    assert.throws(() => installFiles({ ...base, kind: 'hooks', names: ['x'] }), /unknown kind: hooks/);
  });
});
