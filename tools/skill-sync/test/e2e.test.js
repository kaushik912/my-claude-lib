// Real `npx skills` run. Opt-in (needs network/npx): SKILL_SYNC_E2E=1 npm run test:e2e
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { describe, it } from 'node:test';
import { hashDir } from '../src/hash.js';
import { readLockSkills } from '../src/lock.js';
import { install, pull, push, status } from '../src/commands.js';
import { npxAdd } from '../src/npx.js';
import { tmpWorld, writeSkill } from './helpers.js';

describe('e2e with real npx skills', { skip: !process.env.SKILL_SYNC_E2E, timeout: 300000 }, () => {
  it('lib skills/ -> project, update flows down, edit pushes back', () => {
    const w = tmpWorld();
    try {
      const fm = (b) => `---\nname: foo\ndescription: test foo\n---\n${b}\n`;
      writeSkill(w.cfg.libSkills, 'foo', { 'SKILL.md': fm('v1'), 'refs/a.md': 'a', 'z.md': 'z' });

      // a brand-new lib skill shows up as `new`, then installs with the real CLI
      assert.equal(status({ cfg: w.cfg, projectDir: w.projectDir })[0].state, 'new');
      install({ cfg: w.cfg, projectDir: w.projectDir, names: ['foo'], add: npxAdd });
      const projFoo = path.join(w.projectDir, '.agents/skills/foo');
      assert.ok(fs.lstatSync(path.join(w.projectDir, '.claude/skills/foo')).isSymbolicLink());
      // our hash must equal the one npx recorded
      assert.equal(hashDir(projFoo), readLockSkills(w.projectDir).foo.computedHash);

      // lib update -> pull
      fs.writeFileSync(path.join(w.cfg.libSkills, 'foo/SKILL.md'), fm('v2'));
      assert.equal(status({ cfg: w.cfg, projectDir: w.projectDir })[0].state, 'upstream');
      pull({ cfg: w.cfg, projectDir: w.projectDir, add: npxAdd });
      assert.match(fs.readFileSync(path.join(projFoo, 'SKILL.md'), 'utf8'), /v2/);
      assert.equal(status({ cfg: w.cfg, projectDir: w.projectDir })[0].state, 'in-sync');

      // edit in project -> push to lib -> pull settles the stale lock (converged -> in-sync)
      fs.writeFileSync(path.join(projFoo, 'SKILL.md'), fm('v3'));
      push({ cfg: w.cfg, projectDir: w.projectDir });
      assert.match(fs.readFileSync(path.join(w.cfg.libSkills, 'foo/SKILL.md'), 'utf8'), /v3/);
      assert.equal(status({ cfg: w.cfg, projectDir: w.projectDir })[0].state, 'converged');
      pull({ cfg: w.cfg, projectDir: w.projectDir, add: npxAdd });
      assert.equal(status({ cfg: w.cfg, projectDir: w.projectDir })[0].state, 'in-sync');
    } finally {
      w.cleanup();
    }
  });
});
