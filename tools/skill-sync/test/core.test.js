import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { afterEach, beforeEach, describe, it } from 'node:test';
import { hashDir } from '../src/hash.js';
import { classify } from '../src/plan.js';
import { parseSelection } from '../src/pick.js';
import { listAvailable } from '../src/sources.js';
import { install, pull, push, refreshVendored, status, uninstall } from '../src/commands.js';
import { fakeAdd, tmpWorld, writeLockEntry, writeSkill } from './helpers.js';

describe('hashDir', () => {
  let w;
  beforeEach(() => (w = tmpWorld()));
  afterEach(() => w.cleanup());

  it('matches the hash `npx skills` records for a single-file skill', () => {
    // value observed from a real `npx skills add` run
    writeSkill(w.cfg.libSkills, 'foo', '---\nname: foo\ndescription: test foo\n---\nhello\n');
    assert.equal(hashDir(path.join(w.cfg.libSkills, 'foo')), '9b7b3c746adfa49e55443f8c753a3281b62d01db731eacaf64338ed6a1abafd7');
  });

  it('changes when a file is edited, added or removed; null when missing', () => {
    writeSkill(w.cfg.libSkills, 's', { 'SKILL.md': 'a' });
    const dir = path.join(w.cfg.libSkills, 's');
    const base = hashDir(dir);
    fs.writeFileSync(path.join(dir, 'SKILL.md'), 'b');
    const edited = hashDir(dir);
    fs.writeFileSync(path.join(dir, 'extra.md'), 'x');
    const added = hashDir(dir);
    assert.equal(new Set([base, edited, added]).size, 3);
    assert.equal(hashDir(path.join(w.cfg.libSkills, 'nope')), null);
  });
});

describe('classify', () => {
  it('covers every state', () => {
    assert.equal(classify({ src: 'a', lock: 'a', local: 'a' }), 'in-sync');
    assert.equal(classify({ src: 'b', lock: 'a', local: 'a' }), 'upstream');
    assert.equal(classify({ src: 'a', lock: 'a', local: 'c' }), 'local');
    assert.equal(classify({ src: 'b', lock: 'a', local: 'c' }), 'conflict');
    assert.equal(classify({ src: 'b', lock: 'a', local: 'b' }), 'converged');
    assert.equal(classify({ src: null, lock: 'a', local: 'a' }), 'missing-upstream');
    assert.equal(classify({ src: 'a', lock: 'a', local: null }), 'missing-local');
  });
});

describe('listAvailable', () => {
  let w;
  beforeEach(() => (w = tmpWorld()));
  afterEach(() => w.cleanup());

  it('givenMineAndVendored_whenList_thenBothListedWithOrigin', () => {
    writeSkill(w.cfg.libSkills, 'spec', 'v1');
    writeSkill(w.cfg.vendoredSkills, 'caveman', 'v');
    assert.deepEqual(listAvailable(w.cfg).map((s) => [s.name, s.origin]), [['caveman', 'vendored'], ['spec', 'mine']]);
  });

  it('givenSameNameInBoth_whenList_thenMineWins', () => {
    writeSkill(w.cfg.libSkills, 'x', 'mine');
    writeSkill(w.cfg.vendoredSkills, 'x', 'vendored');
    assert.deepEqual(listAvailable(w.cfg).map((s) => s.origin), ['mine']);
  });

  it('givenFolderWithoutSkillMd_whenList_thenIgnored', () => {
    fs.mkdirSync(path.join(w.cfg.libSkills, 'junk'));
    assert.deepEqual(listAvailable(w.cfg), []);
  });
});

describe('install / pull / status (lib -> project)', () => {
  let w, f;
  beforeEach(() => {
    w = tmpWorld();
    f = fakeAdd();
    writeSkill(w.cfg.libSkills, 'spec', 'v1');
    writeSkill(w.cfg.libSkills, 'ticket-fix', 'v1');
    writeSkill(w.cfg.vendoredSkills, 'caveman', 'vendored v1');
  });
  afterEach(() => w.cleanup());

  it('givenUnknownSkill_whenInstall_thenErrorsAndInstallsNothing', () => {
    assert.throws(() => install({ cfg: w.cfg, projectDir: w.projectDir, names: ['spec', 'nope'], add: f.add }), /not in lib: nope/);
    assert.equal(f.calls.length, 0);
  });

  it('givenMineAndVendored_whenInstall_thenEachInstalledFromItsOwnFolder', () => {
    install({ cfg: w.cfg, projectDir: w.projectDir, names: ['spec', 'caveman'], add: f.add });
    const bySource = Object.fromEntries(f.calls.map((c) => [c.sourceDir, c.names]));
    assert.deepEqual(bySource[w.cfg.libSkills], ['spec']);
    assert.deepEqual(bySource[w.cfg.vendoredSkills], ['caveman']);
    assert.ok(status({ cfg: w.cfg, projectDir: w.projectDir }).filter((r) => r.state !== 'new').every((r) => r.state === 'in-sync'));
  });

  it('givenNewSkillInLib_whenPullOrStatus_thenListedAsNewAndNotInstalled', () => {
    install({ cfg: w.cfg, projectDir: w.projectDir, names: ['spec'], add: f.add });
    writeSkill(w.cfg.libSkills, 'hello', 'new');
    f.calls.length = 0;
    const rows = pull({ cfg: w.cfg, projectDir: w.projectDir, add: f.add });
    const hello = rows.find((r) => r.name === 'hello');
    assert.equal(hello.state, 'new');
    assert.match(hello.action, /skill-sync install hello/);
    assert.equal(f.calls.length, 0);
    assert.equal(status({ cfg: w.cfg, projectDir: w.projectDir }).find((r) => r.name === 'hello').state, 'new');
  });

  it('givenLibUpdated_whenPull_thenProjectGetsIt', () => {
    install({ cfg: w.cfg, projectDir: w.projectDir, names: ['spec', 'ticket-fix'], add: f.add });
    writeSkill(w.cfg.libSkills, 'spec', 'v2');
    assert.equal(status({ cfg: w.cfg, projectDir: w.projectDir }).find((r) => r.name === 'spec').state, 'upstream');
    pull({ cfg: w.cfg, projectDir: w.projectDir, add: f.add });
    assert.equal(fs.readFileSync(path.join(w.projectDir, '.agents/skills/spec/SKILL.md'), 'utf8'), 'v2');
    assert.ok(status({ cfg: w.cfg, projectDir: w.projectDir }).filter((r) => r.name !== 'caveman').every((r) => r.state === 'in-sync'));
  });

  it('givenVendoredUpdatedInLib_whenPull_thenProjectGetsIt', () => {
    install({ cfg: w.cfg, projectDir: w.projectDir, names: ['caveman'], add: f.add });
    writeSkill(w.cfg.vendoredSkills, 'caveman', 'vendored v2');
    pull({ cfg: w.cfg, projectDir: w.projectDir, add: f.add });
    assert.equal(fs.readFileSync(path.join(w.projectDir, '.agents/skills/caveman/SKILL.md'), 'utf8'), 'vendored v2');
  });

  it('givenLocalEditAndUpstreamChange_whenPull_thenLocalEditKept', () => {
    install({ cfg: w.cfg, projectDir: w.projectDir, names: ['spec'], add: f.add });
    fs.writeFileSync(path.join(w.projectDir, '.agents/skills/spec/SKILL.md'), 'mine');
    writeSkill(w.cfg.libSkills, 'spec', 'v2');
    f.calls.length = 0;
    const rows = pull({ cfg: w.cfg, projectDir: w.projectDir, add: f.add });
    assert.equal(rows.find((r) => r.name === 'spec').state, 'conflict');
    assert.equal(f.calls.length, 0);
    assert.equal(fs.readFileSync(path.join(w.projectDir, '.agents/skills/spec/SKILL.md'), 'utf8'), 'mine');
  });

  it('givenPullDryRun_whenUpstreamChanged_thenNothingWritten', () => {
    install({ cfg: w.cfg, projectDir: w.projectDir, names: ['spec'], add: f.add });
    writeSkill(w.cfg.libSkills, 'spec', 'v2');
    f.calls.length = 0;
    const rows = pull({ cfg: w.cfg, projectDir: w.projectDir, dryRun: true, add: f.add });
    assert.equal(rows.find((r) => r.name === 'spec').action, 'would-update');
    assert.equal(f.calls.length, 0);
  });
});

describe('push (project -> lib)', () => {
  let w, f;
  const projSkill = (n) => path.join(w.projectDir, '.agents/skills', n, 'SKILL.md');
  beforeEach(() => {
    w = tmpWorld();
    f = fakeAdd();
    writeSkill(w.cfg.libSkills, 'spec', 'v1');
    writeSkill(w.cfg.vendoredSkills, 'caveman', 'vendored');
    install({ cfg: w.cfg, projectDir: w.projectDir, names: ['spec', 'caveman'], add: f.add });
  });
  afterEach(() => w.cleanup());

  it('givenNoLocalChange_whenPush_thenNothingListed', () => {
    assert.deepEqual(push({ cfg: w.cfg, projectDir: w.projectDir }), []);
  });

  it('givenEditedMySkill_whenPush_thenLibUpdated', () => {
    fs.writeFileSync(projSkill('spec'), 'v2');
    fs.writeFileSync(path.join(w.projectDir, '.agents/skills/spec/new.md'), 'n');
    const rows = push({ cfg: w.cfg, projectDir: w.projectDir });
    assert.equal(rows[0].action, 'pushed');
    assert.equal(fs.readFileSync(path.join(w.cfg.libSkills, 'spec/SKILL.md'), 'utf8'), 'v2');
    assert.ok(fs.existsSync(path.join(w.cfg.libSkills, 'spec/new.md')));
  });

  it('givenEditedVendoredSkill_whenPush_thenSkippedAndLibUntouched', () => {
    fs.writeFileSync(projSkill('caveman'), 'tweaked');
    const rows = push({ cfg: w.cfg, projectDir: w.projectDir });
    assert.match(rows[0].action, /not in lib/);
    assert.equal(fs.readFileSync(path.join(w.cfg.vendoredSkills, 'caveman/SKILL.md'), 'utf8'), 'vendored');
    assert.ok(!fs.existsSync(path.join(w.cfg.libSkills, 'caveman')));
  });

  it('givenDryRun_whenPush_thenLibUnchanged', () => {
    fs.writeFileSync(projSkill('spec'), 'v2');
    const rows = push({ cfg: w.cfg, projectDir: w.projectDir, dryRun: true });
    assert.equal(rows[0].action, 'would-push');
    assert.equal(fs.readFileSync(path.join(w.cfg.libSkills, 'spec/SKILL.md'), 'utf8'), 'v1');
  });

  it('givenLibChangedSinceInstall_whenPush_thenConflictUnlessForce', () => {
    fs.writeFileSync(projSkill('spec'), 'proj-edit');
    writeSkill(w.cfg.libSkills, 'spec', 'lib-edit');
    assert.equal(push({ cfg: w.cfg, projectDir: w.projectDir })[0].state, 'conflict');
    assert.equal(fs.readFileSync(path.join(w.cfg.libSkills, 'spec/SKILL.md'), 'utf8'), 'lib-edit');
    push({ cfg: w.cfg, projectDir: w.projectDir, force: true });
    assert.equal(fs.readFileSync(path.join(w.cfg.libSkills, 'spec/SKILL.md'), 'utf8'), 'proj-edit');
  });
});

describe('uninstall (project)', () => {
  let w;
  beforeEach(() => {
    w = tmpWorld();
    writeLockEntry(w.projectDir, 'spec', { source: 'x', sourceType: 'local', computedHash: 'h' });
  });
  afterEach(() => w.cleanup());

  it('givenInstalledSkill_whenRemove_thenRemovesInProjectDir', () => {
    const calls = [];
    const rows = uninstall({ projectDir: w.projectDir, names: ['spec'], remove: (n, cwd) => calls.push([n, cwd]) });
    assert.deepEqual(calls, [['spec', w.projectDir]]);
    assert.deepEqual(rows, [{ name: 'spec', state: 'installed', action: 'removed' }]);
  });

  it('givenDryRun_whenRemove_thenRunsNothing', () => {
    const calls = [];
    const rows = uninstall({ projectDir: w.projectDir, names: ['spec'], dryRun: true, remove: (n) => calls.push(n) });
    assert.equal(calls.length, 0);
    assert.equal(rows[0].action, 'would-remove');
  });

  it('givenNotInstalledOrNoNames_whenRemove_thenRejectedBeforeAnyRemoval', () => {
    const calls = [];
    const remove = (n) => calls.push(n);
    assert.throws(() => uninstall({ projectDir: w.projectDir, names: ['spec', 'nope'], remove }), /not installed in project: nope/);
    assert.throws(() => uninstall({ projectDir: w.projectDir, names: [], remove }), /no skills given/);
    assert.equal(calls.length, 0);
  });
});

describe('refreshVendored (upstream -> lib)', () => {
  let w;
  /** Fakes of `skills remove` / `skills add <source>`: log order, mimic lock + files. */
  const fakes = ({ failAdd = false } = {}) => {
    const calls = [];
    const remove = (name, cwd) => {
      calls.push(['remove', name, cwd]);
      fs.rmSync(path.join(cwd, '.agents/skills', name), { recursive: true, force: true });
      const lockFile = path.join(cwd, 'skills-lock.json');
      const lock = JSON.parse(fs.readFileSync(lockFile, 'utf8'));
      delete lock.skills[name];
      fs.writeFileSync(lockFile, JSON.stringify(lock));
    };
    const addRemote = (source, name, cwd) => {
      calls.push(['add', source, name, cwd]);
      if (failAdd) throw new Error('network down');
      writeSkill(path.join(cwd, '.agents/skills'), name, 'upstream v2');
      writeLockEntry(cwd, name, { source, sourceType: 'github', computedHash: 'h' });
    };
    return { calls, remove, addRemote };
  };
  beforeEach(() => {
    w = tmpWorld();
    writeSkill(w.cfg.vendoredSkills, 'find-docs', 'v1');
    writeSkill(w.cfg.vendoredSkills, 'caveman', 'c1');
    writeSkill(w.cfg.libSkills, 'spec', 'mine');
    for (const n of ['find-docs', 'caveman']) {
      writeLockEntry(w.cfg.registry, n, { source: 'org/repo', sourceType: 'github', computedHash: hashDir(path.join(w.cfg.vendoredSkills, n)) });
    }
    writeLockEntry(w.cfg.registry, 'spec', { source: 'x', sourceType: 'local', computedHash: 'h' });
  });
  afterEach(() => w.cleanup());

  it('givenVendoredSkill_whenRefresh_thenRemovesThenAddsFromLockSource', () => {
    const f = fakes();
    const rows = refreshVendored({ cfg: w.cfg, name: 'find-docs', remove: f.remove, addRemote: f.addRemote });
    assert.deepEqual(f.calls, [
      ['remove', 'find-docs', w.cfg.registry],
      ['add', 'org/repo', 'find-docs', w.cfg.registry],
    ]);
    assert.deepEqual(rows, [{ name: 'find-docs', state: 'upstream', action: 'updated' }]);
    assert.equal(fs.readFileSync(path.join(w.cfg.vendoredSkills, 'find-docs/SKILL.md'), 'utf8'), 'upstream v2');
    assert.equal(fs.readFileSync(path.join(w.cfg.vendoredSkills, 'caveman/SKILL.md'), 'utf8'), 'c1'); // others untouched
  });

  it('givenDryRun_whenRefresh_thenRunsNothing', () => {
    const f = fakes();
    const rows = refreshVendored({ cfg: w.cfg, name: 'find-docs', dryRun: true, remove: f.remove, addRemote: f.addRemote });
    assert.equal(f.calls.length, 0);
    assert.match(rows[0].action, /skills add org\/repo --skill find-docs/);
  });

  it('givenMySkillOrUnknown_whenRefresh_thenRejected', () => {
    const f = fakes();
    for (const name of ['spec', 'nope']) {
      assert.throws(() => refreshVendored({ cfg: w.cfg, name, remove: f.remove, addRemote: f.addRemote }), /not a vendored skill/);
    }
    assert.equal(f.calls.length, 0);
  });

  it('givenAddFails_whenRefresh_thenErrorCarriesRestoreCommand', () => {
    const f = fakes({ failAdd: true });
    assert.throws(
      () => refreshVendored({ cfg: w.cfg, name: 'find-docs', remove: f.remove, addRemote: f.addRemote }),
      /Restore with: skills add org\/repo --skill find-docs -y/,
    );
  });
});

describe('parseSelection', () => {
  const items = ['a', 'b', 'c'];
  it('parses numbers, commas, all, dedupes', () => {
    assert.deepEqual(parseSelection('1 3', items), ['a', 'c']);
    assert.deepEqual(parseSelection('2,2', items), ['b']);
    assert.deepEqual(parseSelection('ALL', items), items);
  });
  it('rejects out-of-range and junk', () => {
    assert.throws(() => parseSelection('4', items), /invalid choice/);
    assert.throws(() => parseSelection('x', items), /invalid choice/);
  });
});
