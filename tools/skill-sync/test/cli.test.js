import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { afterEach, beforeEach, describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';
import { tmpWorld, writeSkill } from './helpers.js';

const BIN = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'bin', 'skill-sync.js');

describe('CLI wiring (offline)', () => {
  let w;
  const run = (...args) => spawnSync('node', [BIN, ...args, '--lib', w.cfg.lib], { cwd: w.projectDir, encoding: 'utf8' });
  const write = (file, text) => {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, text);
  };
  beforeEach(() => {
    w = tmpWorld();
  });
  afterEach(() => w.cleanup());

  it('givenRuleMadeInProject_whenPushAdoptKind_thenInLibAndInSync', () => {
    write(path.join(w.projectDir, '.claude/rules/mine.md'), 'brand new');

    assert.match(run('status', '--kind', 'rules').stdout, /mine\s+untracked/);
    const adopt = run('push', '--adopt', '--kind', 'rules', 'mine');

    assert.equal(adopt.status, 0, adopt.stderr);
    assert.match(adopt.stdout, /mine\s+untracked\s+adopted/);
    assert.equal(fs.readFileSync(path.join(w.cfg.lib, '.claude/rules/mine.md'), 'utf8'), 'brand new');
    assert.match(run('status', '--kind', 'rules').stdout, /mine\s+in-sync/);
  });

  it('givenSkillMadeInProject_whenPushAdoptDryRun_thenReportsAndLibUntouched', () => {
    writeSkill(path.join(w.projectDir, '.agents/skills'), 'mine', 'brand new');

    assert.match(run('status').stdout, /mine\s+untracked/);
    const dry = run('push', '--adopt', 'mine', '--dry-run');

    assert.equal(dry.status, 0, dry.stderr);
    assert.match(dry.stdout, /mine\s+untracked\s+would-adopt/);
    assert.ok(!fs.existsSync(path.join(w.cfg.libSkills, 'mine')));
  });

  it('givenTrackedOrMissingName_whenPushAdopt_thenNonZeroExitWithMessage', () => {
    const r = run('push', '--adopt', '--kind', 'rules', 'ghost');

    assert.equal(r.status, 1);
    assert.match(r.stderr, /not untracked in project: ghost/);
  });
});

describe('status --all-kinds (offline)', () => {
  let w;
  const run = (...args) => spawnSync('node', [BIN, ...args, '--lib', w.cfg.lib], { cwd: w.projectDir, encoding: 'utf8' });
  beforeEach(() => {
    w = tmpWorld();
  });
  afterEach(() => w.cleanup());

  it('givenSkillAndRuleInLib_whenStatusAllKinds_thenBothListedWithKindPrefix', () => {
    writeSkill(w.cfg.libSkills, 'spec', 'a skill');
    fs.mkdirSync(path.join(w.cfg.lib, '.claude/rules'), { recursive: true });
    fs.writeFileSync(path.join(w.cfg.lib, '.claude/rules/spec.md'), 'a rule');

    const r = run('status', '--all-kinds');

    assert.equal(r.status, 0, r.stderr);
    assert.match(r.stdout, /skills\/spec\s+new/);
    assert.match(r.stdout, /rules\/spec\s+new/);
  });

  it('givenAllKindsWithOtherCommand_whenRun_thenNonZeroExit', () => {
    const r = run('pull', '--all-kinds');

    assert.equal(r.status, 1);
    assert.match(r.stderr, /--all-kinds only applies to status/);
  });

  it('givenUnknownCommand_whenRun_thenUsageError', () => {
    const r = run('bogus');

    assert.equal(r.status, 1);
    assert.match(r.stderr, /unknown command: bogus/);
  });
});
