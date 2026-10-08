import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { localSkillsBin } from '../src/npx.js';

describe('localSkillsBin', () => {
  it('givenPinnedInstall_whenResolve_thenReturnsLocalBin', () => {
    assert.match(localSkillsBin(() => true), /skill-sync\/node_modules\/\.bin\/skills$/);
  });

  it('givenNoInstall_whenResolve_thenErrorsWithFixHint', () => {
    assert.throws(() => localSkillsBin(() => false), /skills CLI not installed.*npm install/);
  });
});
