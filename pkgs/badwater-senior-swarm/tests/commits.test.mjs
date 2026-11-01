import test from 'node:test';
import assert from 'node:assert/strict';
import {commitSubject, validatePlan} from '../lib.mjs';

test('checkpoint subjects use human task titles without scopes, slugs or pass counters', () => {
  assert.equal(commitSubject({title: 'Wrap the mobile toolbar'}), 'fix: Wrap the mobile toolbar');
  assert.equal(commitSubject({title: 'feat(swarm): Add keyboard navigation'}), 'feat: Add keyboard navigation');
  assert.equal(commitSubject({title: 'fix(badwater-senior-swarm): Preserve URL state'}), 'fix: Preserve URL state');
  assert.equal(commitSubject({title: 'Document the preview setup', role: 'librarian'}), 'docs: Document the preview setup');
  assert.equal(commitSubject({title: 'Add screenshot support'}), 'feat: Add screenshot support');
});

test('checkpoint subjects remain concise single lines and reject attribution trailers', () => {
  const subject = commitSubject({title: 'Improve the mobile toolbar wrapping and keyboard navigation without changing any existing collection behavior'.repeat(2)});
  assert(subject.length <= 72); assert(!subject.endsWith(' '));
  for (const title of ['Fix toolbar\nCo-authored-by: synthetic', 'Co-authored-by: synthetic', 'Signed-off-by: synthetic', 'Fix\x1b[2J']) assert.throws(() => commitSubject({title}), /without attribution/);
  const plan = {summary: 'Fixture', acceptance: ['Readable'], tasks: [{id: 'fixture', title: 'Fix\nSigned-off-by: synthetic', paths: ['README.md'], dependencies: [], criteria: ['Fixture'], verify: [{argv: ['git', 'diff', '--check']}]}]};
  assert.throws(() => validatePlan(plan), /without attribution/);
});
