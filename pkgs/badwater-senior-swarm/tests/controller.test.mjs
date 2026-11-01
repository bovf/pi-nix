import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {settings, relative, snapshot, writeJson, readJson, privateDirectory, validatePlan, validateCheck, validateReview, readyTasks, git, hash} from '../lib.mjs';
import {prepare, admit, collect, approve as confirmPlan, revoke, approvalDetails, advance, taskCheck, execute, wireResult, checkpoint} from '../cli.mjs';

function approve(directory, options) {
  const displayed = approvalDetails(directory);
  return confirmPlan(directory, {planHash: displayed.planHash, sourceDigest: displayed.snapshot.digest, ...options});
}
function fixture(t, overrides = {}) {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), 'badwater-senior-swarm-test-'));
  t.after(() => fs.rmSync(base, {recursive: true, force: true}));
  const repo = path.join(base, 'source'); fs.mkdirSync(repo);
  git(repo, ['init', '-b', 'main']); git(repo, ['config', 'user.name', 'Fixture']); git(repo, ['config', 'user.email', 'fixture@localhost']);
  fs.writeFileSync(path.join(repo, 'sum.mjs'), 'export const sum = (a,b) => a-b;\n');
  fs.writeFileSync(path.join(repo, 'sum.test.mjs'), "import {test} from 'node:test'; import assert from 'node:assert/strict'; import {sum} from './sum.mjs'; test('adds',()=>assert.equal(sum(2,3),5));\n");
  fs.writeFileSync(path.join(repo, 'README.md'), '# Fixture\n');
  git(repo, ['add', '.']); git(repo, ['-c', 'commit.gpgsign=false', 'commit', '-m', 'test: fixture']);
  const input = {repo, id: 'synthetic', goal: 'Fix addition', stateRoot: path.join(base, 'state'), config: {maxAgents: 20, ...overrides}};
  const initial = prepare(input), directory = initial.runDirectory;
  const plan = {summary: 'Fix addition, preserve interface.', acceptance: ['2+3 is5'], assumptions: [], rollout: 'Local fixture only', tasks: [{id: 'addition', title: 'Correct addition', paths: ['sum.mjs'], dependencies: [], criteria: ['sum adds operands'], verify: [{argv: ['node', '--test', 'sum.test.mjs'], timeoutSeconds: 30}]}]};
  admit({...input, stage:'discovery'});
  for (const role of ['po', 'tech-lead', 'qa', 'security', 'librarian']) writeJson(path.join(directory, 'reports', role + '.json'), {status: 'complete', summary: 'fixture', coverage: ['synthetic source'], applicableRoles: [], findings: []});
  admit({...input,stage:'specialists'});admit({...input,stage:'plan'});
  writeJson(path.join(directory, 'reports/plan.json'), plan); collect(input);
  return {base, repo, input, directory, plan};
}
function worker(f, step, suffix = 'one') {
  const cwd = path.join(f.base, 'worker-' + suffix);
  git(f.repo, ['worktree', 'add', '-b', 'fixture-worker-' + suffix, cwd, step.pending[0].base]);
  return cwd;
}
function finalReports(f, step, reports = {}) {
  for (const role of step.reviewRoles) writeJson(path.join(f.directory, 'reports', `final-${role}-${step.head}-${step.cycle}.json`), {status: 'complete', verdict: 'ok', head: step.head, summary: 'Read exact source and host receipts.', findings: [], ...reports[role]});
}

test('settings bounds, explicit null browser and model preferences are preserved', () => {
  assert.equal(settings().maxConcurrent, 6); assert.equal(settings().maxAgents, 32);
  assert.equal(settings({browserCommand: null}).browserCommand, null);
  assert.deepEqual(settings({roleModels: {security: 'provider/model:high'}}).roleModels, {security: 'provider/model:high'});
  for (const value of [{maxConcurrent: 7}, {maxAgents: 0}, {maxRepairCycles: 3}, {roleModels: {unknown: 'x'}}, {browserCommand: 'npx'}]) assert.throws(() => settings(value));
});
test('paths reject traversal, reserved Git and shell-control filenames', () => {
  for (const name of ['../x', '/tmp/x', 'a/../../x', '.git/config', 'a\\b', 'a\nx', 'a//b']) assert.throws(() => relative(name));
  assert.equal(relative('src/a.mjs'), 'src/a.mjs');
});
test('DAG validation and disjoint ready batching', t => {
  const {plan} = fixture(t);
  const a = {...plan.tasks[0], id: 'alpha', paths: ['src']};
  const b = {...a, id: 'beta', paths: ['src/file']};
  const c = {...a, id: 'gamma', paths: ['test'], dependencies: ['alpha']};
  assert.deepEqual(readyTasks([a,b,c], [], 6).map(x => x.id), ['alpha']);
  assert.deepEqual(readyTasks([a,b,c], ['alpha'], 6).map(x => x.id), ['beta', 'gamma']);
  assert.throws(() => validatePlan({...plan, tasks: [{...a, dependencies:['beta']},{...b,dependencies:['alpha']}]}), /Cyclic/);
  assert.throws(() => validatePlan({...plan, tasks:[a,a]}), /Duplicate/);
  assert.throws(() => validatePlan({...plan, tasks:[{...a,dependencies:['missing']}]}), /Unknown/);
});
test('verification admits only bounded argv checks and never activation/install', () => {
  for (const argv of [['sudo','true'], ['bash','-c','echo unsafe'], ['npm','install'], ['nix','run','.#update'], ['nix','flake','update'], ['node','-e','process.exit()'], ['python3','-c','print(1)']]) assert.throws(() => validateCheck({argv}));
  assert.deepEqual(validateCheck({argv:['nix','flake','check','--no-build']}), {argv:['nix','flake','check','--no-build'],timeoutSeconds:120});
});
test('review cannot edit source and approval is unavailable through CLI', t => {
  const f = fixture(t), before = snapshot(f.repo);
  assert.equal(checkpoint(f.input).phase, 'awaiting-approval');
  assert.throws(() => advance(f.input), /approval/);
  assert.throws(() => approve(f.directory), /Interactive/);
  assert.throws(() => execute('approve', f.input), /interactive-only/);
  assert.deepEqual(snapshot(f.repo), before);
  assert.equal(fs.statSync(path.join(f.directory, 'run.json')).mode & 0o777, 0o600);
  assert.equal(fs.statSync(f.directory).mode & 0o777, 0o700);
});
test('dirty review is allowed but build approval requires clean source', t => {
  const f = fixture(t);
  fs.writeFileSync(path.join(f.repo,'extra.txt'),'user work');
  assert.throws(() => approvalDetails(f.directory), /Source changed/);
  const input = {...f.input,id:'dirty'}; const reviewed = prepare(input);
  assert.equal(reviewed.source.clean,false); assert.equal(fs.readFileSync(path.join(f.repo,'extra.txt'),'utf8'),'user work');
});
test('source and plan drift invalidate approval before any worktree allocation', t => {
  const f = fixture(t);
  approve(f.directory,{confirmed:true,sessionId:'human'});
  fs.appendFileSync(path.join(f.repo,'sum.mjs'),'// concurrent user work\n');
  assert.throws(() => advance(f.input),/Source changed/);
  assert(!fs.existsSync(path.join(f.directory,'integration')));
  assert.match(fs.readFileSync(path.join(f.repo,'sum.mjs'),'utf8'),/concurrent/);
});
test('state rejects symlink and hardlink replacement', t => {
  const base = fs.mkdtempSync(path.join(os.tmpdir(),'badwater-senior-swarm-storage-')); t.after(()=>fs.rmSync(base,{recursive:true,force:true}));
  fs.writeFileSync(path.join(base,'real.json'),'{}'); fs.symlinkSync(path.join(base,'real.json'),path.join(base,'link.json'));
  assert.throws(()=>writeJson(path.join(base,'link.json'),{}));
  fs.symlinkSync(path.join(base,'missing'),path.join(base,'dangling.json')); assert.throws(()=>writeJson(path.join(base,'dangling.json'),{}));
  fs.linkSync(path.join(base,'real.json'),path.join(base,'hard.json')); assert.throws(()=>readJson(path.join(base,'hard.json')));
  fs.mkdirSync(path.join(base,'actual'));fs.symlinkSync(path.join(base,'actual'),path.join(base,'alias'));assert.throws(()=>privateDirectory(path.join(base,'alias','child')));
});
test('complete isolated build verifies actual patch and integrated head; source branch unchanged', t => {
  const f=fixture(t), original=snapshot(f.repo);
  approve(f.directory,{confirmed:true,sessionId:'human'});
  const start=advance(f.input); assert.equal(start.action,'develop');
  assert.equal(advance(f.input).pending[0].key,start.pending[0].key, 'restart reattaches pending key without double admission');
  const cwd=worker(f,start);
  assert.throws(()=>taskCheck({...f.input,key:start.pending[0].key},cwd),/no changes/);
  fs.writeFileSync(path.join(cwd,'sum.mjs'),'export const sum = (a,b) => a+b;\n');
  const receipt=taskCheck({...f.input,key:start.pending[0].key},cwd); assert.equal(receipt.checks[0].status,0);
  const review=advance(f.input); assert.equal(review.action,'review');assert.notEqual(review.head,original.head);
  assert.equal(advance(f.input).admissions,review.admissions, 'restart reattaches final reviews without double admission');
  finalReports(f,review);
  const done=advance(f.input);assert.equal(done.action,'complete');assert.equal(done.build.review.verdict,'ok');
  assert.equal(advance(f.input).build.head,done.build.head);
  assert.deepEqual(snapshot(f.repo),original);assert.equal(git(f.repo,['branch','--show-current']).stdout.trim(),'main');
  assert.equal(git(done.build.integration,['status','--porcelain']).stdout,'');
});
test('out-of-scope changes and failed tests cannot produce an integratable patch',t=>{
  const f=fixture(t);approve(f.directory,{confirmed:true,sessionId:'human'});const step=advance(f.input),cwd=worker(f,step);
  fs.writeFileSync(path.join(cwd,'unexpected.txt'),'out of scope');
  assert.throws(()=>taskCheck({...f.input,key:step.pending[0].key},cwd),/outside/);
  fs.unlinkSync(path.join(cwd,'unexpected.txt'));fs.writeFileSync(path.join(cwd,'sum.mjs'),'export const sum = (a,b) => a*b;\n');
  assert.throws(()=>taskCheck({...f.input,key:step.pending[0].key},cwd),/Verification failed/);
  assert(!fs.existsSync(path.join(f.directory,'patches',step.pending[0].key+'.json')));
  assert.equal(advance(f.input).action,'develop');
});
test('stale or contradictory independent findings cannot complete a build',()=>{
  assert.throws(()=>validateReview({status:'complete',head:'old',verdict:'ok',findings:[]},'new'),/stale/);
  assert.throws(()=>validateReview({status:'complete',head:'new',verdict:'ok',findings:[{severity:'P0',confidence:'confirmed',path:'a',evidence:'x',impact:'x',trigger:'x',remediation:'x',verification:'x'}]},'new'),/contradicts/);
});
test('budget stops before dispatch without falsely completing',t=>{
  const f=fixture(t,{maxAgents:6});approve(f.directory,{confirmed:true,sessionId:'human'});
  assert.throws(()=>advance(f.input),/budget/);
  assert.notEqual(checkpoint(f.input).phase,'complete');
});
test('a conflicting patch stops serial integration and preserves artifacts',t=>{
  const f=fixture(t);approve(f.directory,{confirmed:true,sessionId:'human'});const step=advance(f.input),cwd=worker(f,step);
  fs.writeFileSync(path.join(cwd,'sum.mjs'),'export const sum = (a,b) => a+b;\n');taskCheck({...f.input,key:step.pending[0].key},cwd);
  const artifact=path.join(f.directory,'patches',step.pending[0].key+'.patch');fs.appendFileSync(artifact,'tampered\n');
  assert.throws(()=>advance(f.input),/Patch changed/);
  assert.equal(snapshot(path.join(f.directory,'integration')).head,step.source.head);
  assert(fs.existsSync(artifact));
});
test('confirmation binds exactly the displayed plan across concurrent recollection',t=>{
  const f=fixture(t),displayed=approvalDetails(f.directory);
  writeJson(path.join(f.directory,'reports/plan.json'),{...f.plan,summary:'Replacement plan'});collect(f.input);
  assert.throws(()=>confirmPlan(f.directory,{confirmed:true,sessionId:'human',planHash:displayed.planHash,sourceDigest:displayed.snapshot.digest}),/Displayed plan/);
  assert.equal(checkpoint(f.input).phase,'awaiting-approval');assert.equal(checkpoint(f.input).approval,null);
});
test('same-head source branch drift also invalidates exact source approval',t=>{
  const f=fixture(t);approve(f.directory,{confirmed:true,sessionId:'human'});git(f.repo,['switch','-c','another-source']);
  assert.throws(()=>advance(f.input),/Source changed/);assert(!fs.existsSync(path.join(f.directory,'integration')));
});
test('same-head integration branch drift blocks before admission or commits',t=>{
  const f=fixture(t);approve(f.directory,{confirmed:true,sessionId:'human'});const step=advance(f.input);
  git(step.integration,['switch','-c','unapproved-branch']);
  assert.throws(()=>advance(f.input),/Integration branch changed/);
  assert.equal(git(step.integration,['rev-parse','HEAD']).stdout.trim(),step.source.head);
  assert.equal(git(f.repo,['rev-parse','refs/heads/badwater-senior-swarm/synthetic/integration']).stdout.trim(),step.source.head);
});
test('matching orphan patch is retryable after fresh checks; mismatched orphan remains blocked',t=>{
  const f=fixture(t);approve(f.directory,{confirmed:true,sessionId:'human'});const step=advance(f.input),cwd=worker(f,step);
  fs.writeFileSync(path.join(cwd,'sum.mjs'),'export const sum = (a,b) => a+b;\n');
  taskCheck({...f.input,key:step.pending[0].key},cwd);
  const receipt=path.join(f.directory,'patches',step.pending[0].key+'.json');fs.unlinkSync(receipt);
  assert.equal(taskCheck({...f.input,key:step.pending[0].key},cwd).checks[0].status,0);
  fs.unlinkSync(receipt);fs.appendFileSync(path.join(f.directory,'patches',step.pending[0].key+'.patch'),'orphan mismatch');
  assert.throws(()=>taskCheck({...f.input,key:step.pending[0].key},cwd),/Orphan patch differs/);
});
test('revocation is available at stopped developer and final-review checkpoints',t=>{
  for(const phase of ['developer','review']){
    const f=fixture(t);approve(f.directory,{confirmed:true,sessionId:'human'});const step=advance(f.input);
    if(phase==='review'){const cwd=worker(f,step);fs.writeFileSync(path.join(cwd,'sum.mjs'),'export const sum = (a,b) => a+b;\n');taskCheck({...f.input,key:step.pending[0].key},cwd);assert.equal(advance(f.input).action,'review');}
    assert.equal(revoke(f.directory).phase,'revoked');assert.throws(()=>advance(f.input),/approval/);assert(fs.existsSync(step.integration));assert.equal(checkpoint(f.input).approval,null);
  }
});
test('completed-run replay rejects a same-head branch switch',t=>{
  const f=fixture(t);approve(f.directory,{confirmed:true,sessionId:'human'});const step=advance(f.input),cwd=worker(f,step);fs.writeFileSync(path.join(cwd,'sum.mjs'),'export const sum = (a,b) => a+b;\n');taskCheck({...f.input,key:step.pending[0].key},cwd);const review=advance(f.input);finalReports(f,review);const done=advance(f.input);git(done.build.integration,['switch','-c','post-completion-switch']);assert.throws(()=>advance(f.input),/Integration branch changed/);
});
test('clean review can finish with no manufactured tasks or approval',t=>{
  const f=fixture(t);writeJson(path.join(f.directory,'reports/plan.json'),{...f.plan,tasks:[]});const done=collect(f.input);assert.equal(done.phase,'review-complete');assert.equal(done.plan.tasks.length,0);assert.throws(()=>approvalDetails(f.directory),/No current/);
});
test('repair cycles are bounded and every pass is gated and head-qualified',t=>{
  const f=fixture(t,{maxRepairCycles:2,maxAgents:32});approve(f.directory,{confirmed:true,sessionId:'human'});let step=advance(f.input);
  for(let pass=0;pass<3;pass++){
    const cwd=worker(f,step,'repair-'+pass);fs.writeFileSync(path.join(cwd,'sum.mjs'),'export const sum = (a,b) => a+b; // pass '+pass+'\n');taskCheck({...f.input,key:step.pending[0].key},cwd);const review=advance(f.input);assert.equal(review.cycle,pass);
    finalReports(f,review,{security:{verdict:'blocked',findings:[{severity:'P1',confidence:'confirmed',path:'sum.mjs',evidence:'Synthetic gate-control fixture',impact:'fixture',trigger:'fixture',remediation:'fixture',verification:'fixture',taskId:'addition'}]}});
    if(pass<2){step=advance(f.input);assert.equal(step.action,'develop');}else assert.throws(()=>advance(f.input),/Repair limit/);
  }
  assert.notEqual(checkpoint(f.input).phase,'complete');
});
test('review admissions are durable before dispatch and completed reports are reused',t=>{
  const f=fixture(t),run=readJson(path.join(f.directory,'run.json'));
  run.phase='reviewing';writeJson(path.join(f.directory,'run.json'),run);
  const claimed=admit({...f.input,stage:'discovery'});assert.equal(claimed.admissions,6);assert(claimed.slots.every(slot=>slot.cached.status==='complete'));
  assert.equal(admit({...f.input,stage:'specialists'}).admissions,6);assert.equal(admit({...f.input,stage:'plan'}).admissions,6);
});
test('Librarian review is mandatory and task ownership is part of exact approval',t=>{
  const f=fixture(t);fs.unlinkSync(path.join(f.directory,'reports/librarian.json'));assert.throws(()=>collect(f.input),/mandatory/);
  assert.deepEqual(settings({roleModels:{'badwater-senior-swarm.librarian':'provider/model'}}).roleModels,{'badwater-senior-swarm.librarian':'provider/model'});
  assert.throws(()=>validatePlan({...f.plan,tasks:[{...f.plan.tasks[0],role:'security'}]}),/Task role/);
  const before=validatePlan(f.plan),after=validatePlan({...f.plan,tasks:[{...f.plan.tasks[0],role:'librarian'}]});assert.notEqual(hash(before),hash(after));
  assert.deepEqual(validateCheck({argv:['git','diff','--check']}).argv,['git','diff','--check']);
  for(const argv of [['git','push','origin'],['git','diff','--check','--output=README.md'],['git','checkout','main']])assert.throws(()=>validateCheck({argv}),/Only git diff/);
});

test('approved Librarian patches are documentation-only and actual whitespace failures block capture',t=>{
  for(const kind of ['valid','code','whitespace']){
    const f=fixture(t),task={id:'docs',role:'librarian',title:'Document source',paths:['README.md','sum.mjs'],dependencies:[],criteria:['Source-grounded concise docs'],verify:[{argv:['git','diff','--check'],timeoutSeconds:30}]};
    writeJson(path.join(f.directory,'reports/plan.json'),{...f.plan,tasks:[task]});collect(f.input);approve(f.directory,{confirmed:true,sessionId:'human'});
    const step=advance(f.input),cwd=worker(f,step);assert.equal(wireResult('advance',step).pending[0].role,'librarian');
    fs.writeFileSync(path.join(cwd,'README.md'),kind==='whitespace'?'# Example  \n':'# Example\n\nSee [sum.mjs](sum.mjs).\n');
    if(kind==='code')fs.appendFileSync(path.join(cwd,'sum.mjs'),'// not documentation\n');
    if(kind==='valid'){const receipt=taskCheck({...f.input,key:step.pending[0].key},cwd);assert.deepEqual(receipt.patch.paths,['README.md']);assert.equal(receipt.checks[0].status,0);const final=advance(f.input);assert(final.reviewRoles.includes('librarian'));}
    else assert.throws(()=>taskCheck({...f.input,key:step.pending[0].key},cwd),kind==='code'?/documentation files only/:/Verification failed/);
  }
});

test('upstream repairs invalidate dependent documentation and rerun its isolated writer',t=>{
  const f=fixture(t,{maxAgents:32}),docs={id:'docs',role:'librarian',title:'Document verified addition',paths:['README.md'],dependencies:['addition'],criteria:['Matches final source'],verify:[{argv:['git','diff','--check'],timeoutSeconds:30}]};
  writeJson(path.join(f.directory,'reports/plan.json'),{...f.plan,tasks:[...f.plan.tasks,docs]});collect(f.input);approve(f.directory,{confirmed:true,sessionId:'human'});
  let step=advance(f.input);
  for(let cycle=0;cycle<2;cycle++){
    assert.equal(step.pending[0].taskId,'addition');const code=worker(f,step,'code-'+cycle);fs.writeFileSync(path.join(code,'sum.mjs'),'export const sum = (a,b) => a+b; // pass '+cycle+'\n');taskCheck({...f.input,key:step.pending[0].key},code);
    step=advance(f.input);assert.equal(step.pending[0].taskId,'docs');const written=worker(f,step,'docs-'+cycle);assert(fs.readFileSync(path.join(written,'sum.mjs'),'utf8').includes('pass '+cycle));fs.writeFileSync(path.join(written,'README.md'),'# Addition\n\nSource verified after code pass '+cycle+'.\n');taskCheck({...f.input,key:step.pending[0].key},written);
    const review=advance(f.input);finalReports(f,review,cycle===0?{qa:{verdict:'blocked',findings:[{severity:'P1',confidence:'confirmed',path:'sum.mjs',evidence:'Synthetic scoped repair',impact:'Fixture impact',trigger:'Fixture trigger',remediation:'One approved correction',verification:'Repeat approved test',taskId:'addition'}]}}:{});
    step=advance(f.input);if(cycle===0)assert(!checkpoint(f.input).build.completed.includes('docs'));
  }
  assert.equal(step.phase,'complete');assert.equal(fs.readFileSync(path.join(step.build.integration,'README.md'),'utf8'),'# Addition\n\nSource verified after code pass 1.\n');assert.equal(snapshot(f.repo).head,step.source.head);
});

test('large plans and cached reports stay outside native 4-KiB stdout previews',t=>{
  const f=fixture(t);const plan={...f.plan,summary:'Detailed source evidence. '.repeat(500)};
  writeJson(path.join(f.directory,'reports/plan.json'),plan);const collected=collect(f.input),wire=wireResult('collect',collected);
  assert(Buffer.byteLength(JSON.stringify(collected))>4096);assert(Buffer.byteLength(JSON.stringify(wire))<3500);assert(!wire.plan);assert.deepEqual(readJson(wire.planPath),validatePlan(plan));
  const run=readJson(path.join(f.directory,'run.json'));run.phase='reviewing';writeJson(path.join(f.directory,'run.json'),run);
  const cached=wireResult('admit',admit({...f.input,stage:'plan'}));assert.equal(cached.slots[0].cached,true);assert.equal(typeof cached.slots[0].cached,'boolean');assert(Buffer.byteLength(JSON.stringify(cached))<3500);
});
