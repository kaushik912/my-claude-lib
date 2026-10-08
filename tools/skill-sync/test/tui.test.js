import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { afterEach, beforeEach, describe, it } from 'node:test';
import { buildCalls, buildChoices, runTui } from '../src/tui.js';
import { fakeAdd, tmpWorld, writeSkill } from './helpers.js';

/** Scripted prompt adapter: answers are consumed in order; notes/outros are recorded. */
function fakeUi(answers) {
  const log = { notes: [], outro: [] };
  const next = async () => (answers.length ? answers.shift() : null);
  return { log, ui: { intro() {}, outro: (t) => log.outro.push(t), note: (t, title) => log.notes.push({ title, text: t }), select: next, multiselect: next, confirm: async () => (await next()) === true } };
}

describe('tui flow (injected prompts, same dispatch as the CLI)', () => {
  let w, f, base;
  const skillFile = (name) => path.join(w.projectDir, '.agents/skills', name, 'SKILL.md');
  beforeEach(() => {
    w = tmpWorld();
    f = fakeAdd();
    base = { cfg: w.cfg, projectDir: w.projectDir, add: f.add, remove: () => {}, addRemote: () => {} };
    writeSkill(w.cfg.libSkills, 'x', 'x v1');
    writeSkill(w.cfg.libSkills, 'y', 'y v1');
    fs.mkdirSync(path.join(w.cfg.lib, '.claude/rules'), { recursive: true });
    fs.writeFileSync(path.join(w.cfg.lib, '.claude/rules/r.md'), 'rule v1');
    fs.mkdirSync(path.join(w.cfg.lib, '.claude-plugin'), { recursive: true });
    fs.writeFileSync(path.join(w.cfg.lib, '.claude-plugin/marketplace.json'), JSON.stringify({ plugins: [{ name: 'b', version: '1.0.0', skills: ['./skills/x', './skills/y'] }] }));
  });
  afterEach(() => w.cleanup());

  it('givenSkillAndRuleSelected_whenInstall_thenBothInstalled', async () => {
    const { ui } = fakeUi(['install', ['skills/x', 'rules/r'], true]);

    await runTui({ base, ui });

    assert.ok(fs.existsSync(skillFile('x')));
    assert.equal(fs.readFileSync(path.join(w.projectDir, '.claude/rules/r.md'), 'utf8'), 'rule v1');
    assert.ok(!fs.existsSync(skillFile('y')));
  });

  it('givenBundleSelected_whenInstall_thenAllItsSkillsInstalled', async () => {
    const { ui } = fakeUi(['install', ['bundle:b'], true]);

    await runTui({ base, ui });

    assert.ok(fs.existsSync(skillFile('x')) && fs.existsSync(skillFile('y')));
  });

  it('givenBundleWithInstalledSkill_whenChoices_thenOnlyMissingCounted', async () => {
    await runTui({ base, ui: fakeUi(['install', ['skills/x'], true]).ui });
    const rows = (await import('../src/ops.js')).statusAll(base);

    const bundle = buildChoices('install', rows, [{ name: 'b', version: '1.0.0', skills: ['x', 'y'] }]).find((c) => c.value === 'bundle:b');

    assert.match(bundle.hint, /1 skill/);
    assert.deepEqual(buildCalls('install', ['bundle:b'], rows, w.cfg), [{ kind: 'skills', names: ['y'], adopt: false }]);
  });

  it('givenLibUpdated_whenPullDeclined_thenPreviewShownAndNothingChanges', async () => {
    await runTui({ base, ui: fakeUi(['install', ['skills/x'], true]).ui });
    writeSkill(w.cfg.libSkills, 'x', 'x v2');
    const { ui, log } = fakeUi(['pull', ['skills/x'], false]);

    await runTui({ base, ui });

    assert.match(log.notes.find((n) => n.title.startsWith('preview')).text, /-x v1\n\s+\+x v2/);
    assert.equal(fs.readFileSync(skillFile('x'), 'utf8'), 'x v1');
    assert.match(log.outro.at(-1), /nothing changed/);
  });

  it('givenLibUpdated_whenPullConfirmed_thenProjectUpdated', async () => {
    await runTui({ base, ui: fakeUi(['install', ['skills/x'], true]).ui });
    writeSkill(w.cfg.libSkills, 'x', 'x v2');

    await runTui({ base, ui: fakeUi(['pull', ['skills/x'], true]).ui });

    assert.equal(fs.readFileSync(skillFile('x'), 'utf8'), 'x v2');
  });

  it('givenRuleMadeInProject_whenPushConfirmed_thenAdoptedIntoLib', async () => {
    fs.mkdirSync(path.join(w.projectDir, '.claude/rules'), { recursive: true });
    fs.writeFileSync(path.join(w.projectDir, '.claude/rules/mine.md'), 'brand new');

    await runTui({ base, ui: fakeUi(['push', ['rules/mine'], true]).ui });

    assert.equal(fs.readFileSync(path.join(w.cfg.lib, '.claude/rules/mine.md'), 'utf8'), 'brand new');
  });

  it('givenCancelAtActionOrSelection_whenRun_thenNothingChanges', async () => {
    await runTui({ base, ui: fakeUi([null]).ui });
    await runTui({ base, ui: fakeUi(['install', null]).ui });

    assert.ok(!fs.existsSync(skillFile('x')));
    assert.equal(f.calls.length, 0);
  });
});
