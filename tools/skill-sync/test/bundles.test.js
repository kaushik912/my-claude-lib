import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { afterEach, beforeEach, describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';
import { bundleSkills, readBundles } from '../src/bundles.js';
import { tmpWorld } from './helpers.js';

const BIN = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'bin', 'skill-sync.js');

describe('bundles', () => {
  let w;
  beforeEach(() => {
    w = tmpWorld();
    fs.mkdirSync(path.join(w.cfg.lib, '.claude-plugin'), { recursive: true });
    fs.writeFileSync(
      path.join(w.cfg.lib, '.claude-plugin/marketplace.json'),
      JSON.stringify({ plugins: [
        { name: 'a', version: '1.0.0', skills: ['./skills/x', './skills/y'] },
        { name: 'b', version: '0.1.0', skills: ['./skills/y', './skills/z'] },
      ] }),
    );
  });
  afterEach(() => w.cleanup());

  it('givenMarketplace_whenReadBundles_thenNamesVersionsAndSkillNames', () => {
    assert.deepEqual(readBundles(w.cfg)[0], { name: 'a', version: '1.0.0', skills: ['x', 'y'] });
  });

  it('givenNoMarketplace_whenReadBundles_thenEmpty', () => {
    fs.rmSync(path.join(w.cfg.lib, '.claude-plugin'), { recursive: true });

    assert.deepEqual(readBundles(w.cfg), []);
  });

  it('givenOverlappingBundles_whenBundleSkills_thenDedupedInOrder', () => {
    assert.deepEqual(bundleSkills(w.cfg, ['a', 'b']), ['x', 'y', 'z']);
  });

  it('givenUnknownBundle_whenBundleSkills_thenErrorListsAvailable', () => {
    assert.throws(() => bundleSkills(w.cfg, ['nope']), /unknown bundle: nope \(available: a, b\)/);
  });

  it('givenBundleWithOtherCommand_whenRun_thenNonZeroExit', () => {
    const r = spawnSync('node', [BIN, 'pull', '--bundle', 'a', '--lib', w.cfg.lib], { cwd: w.projectDir, encoding: 'utf8' });

    assert.equal(r.status, 1);
    assert.match(r.stderr, /--bundle only applies to skills install/);
  });

  it('givenUnknownBundle_whenInstall_thenNonZeroExitAndNothingInstalled', () => {
    const r = spawnSync('node', [BIN, 'install', '--bundle', 'nope', '--lib', w.cfg.lib], { cwd: w.projectDir, encoding: 'utf8' });

    assert.equal(r.status, 1);
    assert.match(r.stderr, /unknown bundle: nope/);
  });
});
