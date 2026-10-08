import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { afterEach, beforeEach, describe, it } from 'node:test';
import { buildCalls, buildChoices, groupByKind, runTui } from '../src/tui.js';
import { fakeAdd, tmpWorld, writeSkill } from './helpers.js';

/** Scripted prompt adapter: answers are consumed in order; notes/outros are recorded. */
function fakeUi(answers) {
  const log = { notes: [], outro: [], prompts: [] };
  const next = (type) => async (o) => { log.prompts.push({ type, ...o }); return answers.length ? answers.shift() : null; };
  return { log, ui: { intro() {}, outro: (t) => log.outro.push(t), note: (t, title) => log.notes.push({ title, text: t }), select: next('select'), multiselect: next('multiselect'), groupMultiselect: next('groupMultiselect'), confirm: async (o) => (await next('confirm')(o)) === true } };
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
    const { ui } = fakeUi(['install', 'all', ['skills/x', 'rules/r'], true]);

    await runTui({ base, ui });

    assert.ok(fs.existsSync(skillFile('x')));
    assert.equal(fs.readFileSync(path.join(w.projectDir, '.claude/rules/r.md'), 'utf8'), 'rule v1');
    assert.ok(!fs.existsSync(skillFile('y')));
  });

  it('givenBundleSelected_whenInstall_thenAllItsSkillsInstalled', async () => {
    const { ui } = fakeUi(['install', 'skills', ['bundle:b'], true]);

    await runTui({ base, ui });

    assert.ok(fs.existsSync(skillFile('x')) && fs.existsSync(skillFile('y')));
  });

  it('givenBundleWithInstalledSkill_whenChoices_thenOnlyMissingCounted', async () => {
    await runTui({ base, ui: fakeUi(['install', 'skills', ['skills/x'], true]).ui });
    const rows = (await import('../src/ops.js')).statusAll(base);

    const bundle = buildChoices('install', rows, [{ name: 'b', version: '1.0.0', skills: ['x', 'y'] }]).find((c) => c.value === 'bundle:b');

    assert.match(bundle.hint, /1 skill/);
    assert.deepEqual(buildCalls('install', ['bundle:b'], rows, w.cfg), [{ kind: 'skills', names: ['y'], adopt: false }]);
  });

  it('givenLibUpdated_whenPullDeclined_thenPreviewShownAndNothingChanges', async () => {
    await runTui({ base, ui: fakeUi(['install', 'skills', ['skills/x'], true]).ui });
    writeSkill(w.cfg.libSkills, 'x', 'x v2');
    const { ui, log } = fakeUi(['pull', ['skills/x'], false]);

    await runTui({ base, ui });

    assert.match(log.notes.find((n) => n.title.startsWith('preview')).text, /-x v1\n\s+\+x v2/);
    assert.equal(fs.readFileSync(skillFile('x'), 'utf8'), 'x v1');
    assert.match(log.outro.at(-1), /nothing changed/);
  });

  it('givenLibUpdated_whenPullConfirmed_thenProjectUpdated', async () => {
    await runTui({ base, ui: fakeUi(['install', 'skills', ['skills/x'], true]).ui });
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

  it('givenSeveralKinds_whenInstallAll_thenGroupedListWithBundlesFirst', async () => {
    const { ui, log } = fakeUi(['install', 'all', null]);

    await runTui({ base, ui });

    const picker = log.prompts[1];
    assert.deepEqual(picker.options.map((o) => o.value), ['all', 'skills', 'rules']);
    const grouped = log.prompts[2];
    assert.equal(grouped.type, 'groupMultiselect');
    assert.deepEqual(Object.keys(grouped.options), ['bundles', 'skills', 'rules']);
    assert.deepEqual(grouped.options.skills.map((o) => o.value), ['skills/x', 'skills/y']);
  });

  it('givenSeveralKinds_whenPickRules_thenFlatListOfThatKindOnly', async () => {
    const { ui, log } = fakeUi(['install', 'rules', ['rules/r'], true]);

    await runTui({ base, ui });

    assert.equal(log.prompts[2].type, 'multiselect');
    assert.deepEqual(log.prompts[2].options.map((o) => o.value), ['rules/r']);
    assert.ok(!fs.existsSync(skillFile('x')));
  });

  it('givenSkillsKind_whenPicked_thenBundlesListedOnTop', async () => {
    const { ui, log } = fakeUi(['install', 'skills', null]);

    await runTui({ base, ui });

    assert.deepEqual(log.prompts[2].options.map((o) => o.value), ['bundle:b', 'skills/x', 'skills/y']);
  });

  it('givenOnlyOneKindHasItems_whenInstall_thenPickerSkipped', async () => {
    fs.rmSync(path.join(w.cfg.lib, '.claude/rules'), { recursive: true });
    const { ui, log } = fakeUi(['install', ['skills/x'], true]);

    await runTui({ base, ui });

    assert.deepEqual(log.prompts.map((p) => p.type), ['select', 'multiselect', 'confirm']);
    assert.ok(fs.existsSync(skillFile('x')));
  });

  it('givenChoices_whenGroupByKind_thenBundlesFoldIntoSkills', () => {
    const choices = [{ value: 'bundle:b' }, { value: 'skills/x' }, { value: 'rules/r' }];

    assert.deepEqual(groupByKind(choices), { skills: [{ value: 'bundle:b' }, { value: 'skills/x' }], rules: [{ value: 'rules/r' }] });
  });

  it('givenCancelAtActionOrSelection_whenRun_thenNothingChanges', async () => {
    await runTui({ base, ui: fakeUi([null]).ui });
    await runTui({ base, ui: fakeUi(['install', 'all', null]).ui });

    assert.ok(!fs.existsSync(skillFile('x')));
    assert.equal(f.calls.length, 0);
  });
});
