import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {ROOT, ROLES, settings, runDirectory, git} from '../lib.mjs';
import {prepare} from '../cli.mjs';

test('package and explicit skill use the complete public brand', () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(ROOT, 'package.json'), 'utf8'));
  assert.equal(manifest.name, 'badwater-senior-swarm');
  assert.deepEqual(manifest.pi.skills, ['./skills/badwater-senior-swarm']);
  const skill = fs.readFileSync(path.join(ROOT, 'skills/badwater-senior-swarm/SKILL.md'), 'utf8');
  assert.match(skill, /^name: badwater-senior-swarm$/m);
  assert.match(skill, /\/skill:badwater-senior-swarm review/);
  assert(!fs.existsSync(path.join(ROOT, 'skills/swarm')));
  for (const role of [...ROLES, 'developer']) {
    assert.match(fs.readFileSync(path.join(ROOT, 'agents', role + '.md'), 'utf8'), /^package: badwater-senior-swarm$/m);
  }
  assert.deepEqual(settings({roleModels: {'badwater-senior-swarm.qa': 'provider/model'}}).roleModels, {'badwater-senior-swarm.qa': 'provider/model'});
  assert.throws(() => settings({roleModels: {'swarm.qa': 'provider/model'}}), /Invalid role/);
});

test('renamed storage starts separately without moving or approving prior artifacts', t => {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), 'badwater-senior-swarm-rename-'));
  t.after(() => fs.rmSync(base, {recursive: true, force: true}));
  const repo = path.join(base, 'repo'); fs.mkdirSync(repo);
  git(repo, ['init', '-b', 'main']); git(repo, ['config', 'user.name', 'Fixture']); git(repo, ['config', 'user.email', 'fixture@localhost']);
  fs.writeFileSync(path.join(repo, 'fixture.txt'), 'Synthetic rename fixture\n'); git(repo, ['add', '.']); git(repo, ['-c', 'commit.gpgsign=false', 'commit', '-m', 'test: storage fixture']);
  const state = path.join(base, 'state'), legacy = path.join(state, 'badwater-swarm');
  fs.mkdirSync(legacy, {recursive: true});
  const sentinel = path.join(legacy, 'prior-run.json'), bytes = '{"approval":"synthetic-prior-authority"}\n'; fs.writeFileSync(sentinel, bytes);
  const previous = process.env.XDG_STATE_HOME; process.env.XDG_STATE_HOME = state;
  try {
    const directory = runDirectory(repo, 'renamed');
    assert(directory.startsWith(path.join(state, 'badwater-senior-swarm') + path.sep));
    const result = prepare({repo, id: 'renamed', goal: 'Source review only'});
    assert.equal(result.runDirectory, directory); assert.equal(result.phase, 'reviewing');
    const run = JSON.parse(fs.readFileSync(path.join(directory, 'run.json'), 'utf8')); assert(!run.approval);
    assert.equal(fs.readFileSync(sentinel, 'utf8'), bytes);
  } finally { if (previous === undefined) delete process.env.XDG_STATE_HOME; else process.env.XDG_STATE_HOME = previous; }
});
