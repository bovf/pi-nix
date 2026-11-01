#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {ROOT, hash, ensure, settings, identifier, relative, beneath, privateDirectory, readJson, writeJson, command, git, repository, snapshot, runDirectory, locked, validatePlan, validateReview, readyTasks, loadPaths} from './lib.mjs';

const manifest = directory => path.join(directory, 'run.json');
function load(input) {
  const repo = repository(input.repo);
  const directory = runDirectory(repo, input.id, input.stateRoot);
  const run = readJson(manifest(directory));
  ensure(run.version === 1 && run.repo === repo && run.id === input.id, 'Swarm run identity mismatch');
  ensure(run.runtimeRoot === ROOT, 'Runtime package changed; start a new reviewed run instead of reusing authority');
  return {run, directory};
}
function save(directory, run) { writeJson(manifest(directory), run); return run; }
function assertSource(run) { ensure(snapshot(run.repo).digest === run.snapshot.digest, 'Source changed since review/approval; start a new review, do not reuse approval'); }
function result(run, directory, extra = {}) { return {id: run.id, runDirectory: directory, phase: run.phase, source: run.snapshot, admissions: run.admissions, completed: run.build?.completed || [], config: run.config, ...extra}; }
export function prepare(input) {
  ensure(typeof input.goal === 'string' && input.goal.trim() && input.goal.length <= 4000, 'A bounded goal is required');
  const config = settings(input.config), source = snapshot(input.repo);
  const directory = runDirectory(source.repo, input.id, input.stateRoot);
  return locked(directory, () => {
    if (fs.existsSync(manifest(directory))) {
      const old = readJson(manifest(directory));
      ensure(old.runtimeRoot === ROOT && old.goal === input.goal && old.snapshot.digest === source.digest && hash(old.config) === hash(config), 'Existing id has different runtime/goal/source/config; use a new id');
      return result(old, directory, {goal: old.goal, config: old.config});
    }
    privateDirectory(path.join(directory, 'reports'));
    const run = {version: 1, runtimeRoot: ROOT, id: identifier(input.id), repo: source.repo, goal: input.goal, snapshot: source, config, phase: 'reviewing', admissions: 0, reviewClaims: {}, createdAt: new Date().toISOString()};
    save(directory, run);
    return result(run, directory, {goal: run.goal, config});
  });
}
export function admit(input) {
  const {directory} = load(input);
  return locked(directory, () => {
    const {run} = load(input); assertSource(run);
    ensure(run.phase === 'reviewing', 'Review is already finalized; use its plan instead of respawning the team');
    let names;
    if (input.stage === 'discovery') names = ['po', 'tech-lead'];
    else if (input.stage === 'specialists') {
      const technical = readJson(path.join(directory, 'reports/tech-lead.json'));
      ensure(technical.status === 'complete' && Array.isArray(technical.applicableRoles), 'Technical discovery incomplete');
      names = [...new Set(['qa', 'security', ...technical.applicableRoles.filter(role => ['ui', 'ux', 'devops'].includes(role))])];
    } else { ensure(input.stage === 'plan', 'Unknown review admission stage'); names = ['plan']; }
    const fresh = names.filter(name => !run.reviewClaims[name]);
    ensure(run.admissions + fresh.length <= run.config.maxAgents, 'Review agent budget exhausted before dispatch');
    fresh.forEach(name => { run.reviewClaims[name] = true; }); run.admissions += fresh.length; save(directory, run);
    return result(run, directory, {slots: names.map(name => {
      const file = path.join(directory, 'reports', name + '.json');
      let cached;
      if (!fresh.includes(name) && fs.existsSync(file)) {
        try { const report = readJson(file); cached = name === 'plan' ? validatePlan(report) : report.status === 'complete' ? report : undefined; } catch { /* Invalid partial report requires this same admitted lane to retry. */ }
      }
      return {name, ...(cached ? {cached} : {})};
    })});
  });
}
export function collect(input) {
  const {directory} = load(input);
  return locked(directory, () => {
    const {run} = load(input); assertSource(run);
    ensure(['reviewing', 'awaiting-approval'].includes(run.phase), 'Review cannot overwrite an approved/building run');
    const reports = fs.readdirSync(path.join(directory, 'reports')).filter(x => /^[a-z-]+\.json$/.test(x));
    for (const required of ['po.json', 'tech-lead.json', 'qa.json', 'security.json', 'plan.json']) ensure(reports.includes(required), 'Missing mandatory review report');
    for (const file of reports.filter(x => x !== 'plan.json')) {
      const report = readJson(path.join(directory, 'reports', file));
      ensure(report.status === 'complete' && Array.isArray(report.coverage) && Array.isArray(report.findings), 'Specialist did not finish; report the coverage gap');
    }
    const plan = validatePlan(readJson(path.join(directory, 'reports/plan.json')));
    ensure(reports.every(file => run.reviewClaims[file.slice(0, -5)]), 'Report has no durable child admission');
    run.plan = plan; run.planHash = hash(plan);
    run.finalRoles = ['qa', 'security', ...['ui', 'ux'].filter(role => reports.includes(role + '.json'))];
    ensure(run.admissions <= run.config.maxAgents, 'Review exceeded its child budget');
    writeJson(path.join(directory, 'plan.json'), plan);
    run.phase = plan.tasks.length ? 'awaiting-approval' : 'review-complete'; save(directory, run);
    return result(run, directory, {plan, planHash: run.planHash, next: plan.tasks.length ? `/swarm-approve ${directory}` : 'No implementation justified; review complete.'});
  });
}
export function approvalDetails(directory) {
  const run = readJson(manifest(directory));
  ensure(run.runtimeRoot === ROOT, 'Runtime package changed; review again');
  ensure(run.phase === 'awaiting-approval' && run.planHash === hash(validatePlan(run.plan)), 'No current review plan awaits approval');
  assertSource(run);
  ensure(run.snapshot.clean && snapshot(run.repo).clean, 'Build isolation requires a clean source checkout; review is still available');
  return run;
}
export function approve(directory, {confirmed = false, sessionId, planHash, sourceDigest} = {}) {
  ensure(confirmed && typeof sessionId === 'string' && sessionId.length > 0, 'Interactive human approval is required');
  return locked(directory, () => {
    const run = approvalDetails(directory);
    ensure(planHash === run.planHash && sourceDigest === run.snapshot.digest, 'Displayed plan/source changed during confirmation; review and confirm again');
    run.approval = {planHash: run.planHash, sourceDigest: run.snapshot.digest, sessionId, at: new Date().toISOString(), authority: 'local integration worktrees, approved checks and local checkpoint commits only'};
    run.phase = 'approved'; save(directory, run);
    return result(run, directory);
  });
}
export function revoke(directory) {
  return locked(directory, () => {
    const run = readJson(manifest(directory));
    // Persistent build phase is not proof of a live workflow. Revoke future
    // admission even at a stopped developer/reviewer checkpoint; never delete it.
    delete run.approval; run.phase = 'revoked'; save(directory, run); return result(run, directory);
  });
}
function assertApproval(run) {
  ensure(run.approval && run.approval.planHash === hash(validatePlan(run.plan)) && run.approval.sourceDigest === run.snapshot.digest, 'No matching human plan/source approval; use /swarm-approve');
  ensure(run.phase !== 'complete' && run.phase !== 'revoked', 'Run is already terminal');
  assertSource(run); ensure(snapshot(run.repo).clean, 'Build source must remain clean');
}
function assertIntegration(run) {
  const current = snapshot(run.build.integration);
  const branch = git(run.build.integration, ['symbolic-ref', '--quiet', 'HEAD'], {allowFailure: true});
  ensure(branch.status === 0 && branch.stdout.trim() === `refs/heads/${run.build.branch}`, 'Integration branch changed; no automatic checkout or commit');
  ensure(current.clean && current.head === run.build.head, 'Integration checkout changed; preserve and inspect it');
}
function commit(cwd, title) {
  git(cwd, ['-c', 'user.name=Badwater Swarm', '-c', 'user.email=swarm@localhost', '-c', 'commit.gpgsign=false', 'commit', '-m', title]);
  return git(cwd, ['rev-parse', 'HEAD']).stdout.trim();
}
function runChecks(cwd, checks, receiptDirectory) {
  privateDirectory(receiptDirectory);
  return checks.map((check, index) => {
    const argv = [...check.argv]; if (argv[0] === 'node') argv[0] = loadPaths().node;
    const execution = command(argv, cwd, {timeout: check.timeoutSeconds * 1000, allowFailure: true});
    const receipt = {argv: check.argv, cwd, head: git(cwd, ['rev-parse', 'HEAD']).stdout.trim(), ...execution};
    writeJson(path.join(receiptDirectory, `check-${index}.json`), receipt);
    ensure(!execution.error && execution.status === 0, `Verification failed; inspect private receipts in ${receiptDirectory}`);
    return {argv: check.argv, status: execution.status, receipt: path.join(receiptDirectory, `check-${index}.json`)};
  });
}
function capturePatch(cwd, base, scopes, directory, key) {
  const index = path.join(directory, `.index-${crypto.randomUUID()}`);
  const env = {GIT_INDEX_FILE: index};
  try {
    git(cwd, ['read-tree', base], {env});
    git(cwd, ['add', '-A', '--', '.'], {env});
    const names = git(cwd, ['diff', '--cached', '--name-only', '-z', base, '--'], {env}).stdout.split('\0').filter(Boolean);
    ensure(names.length > 0, 'Developer made no changes; not implemented');
    for (const file of names) {
      relative(file); ensure(scopes.some(scope => beneath(file, scope)), 'Developer changed a path outside its approved task');
      let current = cwd;
      for (const piece of file.split('/')) {
        current = path.join(current, piece);
        if (fs.existsSync(current)) ensure(!fs.lstatSync(current).isSymbolicLink(), 'Changed paths cannot traverse or create symlinks');
      }
    }
    const treeEntries = git(cwd, ['ls-files', '--stage', '-z', '--', ...names], {env}).stdout.split('\0');
    ensure(!treeEntries.some(entry => /^(120000|160000) /.test(entry)), 'Symlink/submodule patches require a separately reviewed workflow');
    const patch = git(cwd, ['diff', '--cached', '--binary', '--no-ext-diff', '--no-textconv', base, '--'], {env}).stdout;
    const file = path.join(directory, 'patches', `${key}.patch`);
    return {file, hash: hash(patch), paths: names, content: patch};
  } finally { for (const suffix of ['', '.lock']) fs.rmSync(index + suffix, {force: true}); }
}
export function taskCheck(input, cwd = process.cwd()) {
  const {run, directory} = load(input); assertApproval(run);
  if (run.build) assertIntegration(run);
  ensure(run.build && run.build.pending?.some(x => x.key === input.key), 'Task is not admitted by the controller');
  const item = run.build.pending.find(x => x.key === input.key);
  const task = run.plan.tasks.find(x => x.id === item.taskId);
  const actual = repository(cwd);
  ensure(actual !== run.repo && actual !== run.build.integration, 'Developer verification requires its own worktree');
  const common = cwd => fs.realpathSync(path.resolve(cwd, git(cwd, ['rev-parse', '--git-common-dir']).stdout.trim()));
  ensure(common(actual) === common(run.repo), 'Developer worktree belongs to another repository');
  ensure(git(actual, ['rev-parse', 'HEAD']).stdout.trim() === item.base, 'Developer changed its base/committed; only the integrator may commit');
  ensure(git(actual, ['diff', '--cached', '--name-only']).stdout.trim() === '', 'Developer must leave no staged files');
  const target = path.join(directory, 'patches', `${item.key}.json`);
  if (fs.existsSync(target)) {
    const old = readJson(target);
    ensure(old.worktreeDigest === snapshot(actual).digest, 'Task changed after its captured gate; do not reuse stale verification');
    return old;
  }
  const before = snapshot(actual);
  const captured = capturePatch(actual, item.base, task.paths, directory, item.key);
  const checks = runChecks(actual, task.verify, path.join(directory, 'checks', item.key));
  ensure(snapshot(actual).digest === before.digest, 'Verification mutated repository source; capture and inspect it, do not integrate');
  const {content, ...patch} = captured;
  privateDirectory(path.dirname(patch.file));
  let orphan; try { orphan = fs.lstatSync(patch.file); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  if (orphan) ensure(orphan.isFile() && !orphan.isSymbolicLink() && orphan.nlink === 1 && hash(fs.readFileSync(patch.file)) === patch.hash, 'Orphan patch differs from freshly verified work; preserve it for reconciliation');
  else fs.writeFileSync(patch.file, content, {mode: 0o600, flag: 'wx'});
  const receipt = {taskId: task.id, key: item.key, base: item.base, worktree: actual, worktreeDigest: before.digest, patch, checks};
  writeJson(target, receipt);
  return {taskId: task.id, key: item.key, checks, patch};
}
function integrate(run, directory) {
  for (const item of run.build.pending) {
    const receipt = readJson(path.join(directory, 'patches', `${item.key}.json`));
    ensure(receipt.key === item.key && receipt.taskId === item.taskId && receipt.base === item.base && receipt.checks?.length > 0, 'Missing or mismatched developer verification');
    const file = receipt.patch?.file;
    ensure(file === path.join(directory, 'patches', `${item.key}.patch`), 'Unexpected patch artifact path');
    const info = fs.lstatSync(file); ensure(info.isFile() && info.nlink === 1 && !info.isSymbolicLink(), 'Unsafe patch artifact');
    ensure(hash(fs.readFileSync(file)) === receipt.patch.hash, 'Patch changed after verification');
    const cwd = run.build.integration;
    assertIntegration(run);
    git(cwd, ['apply', '--check', '--index', file]);
    git(cwd, ['apply', '--index', file]);
    run.build.head = commit(cwd, `feat(swarm): ${item.taskId} pass ${run.build.cycle}`);
    run.build.completed = [...new Set([...run.build.completed, item.taskId])];
    run.build.integrated.push({key: item.key, taskId: item.taskId, head: run.build.head, patchHash: receipt.patch.hash, checks: receipt.checks});
    run.build.pending = run.build.pending.filter(x => x.key !== item.key);
    save(directory, run);
  }
}
export function advance(input) {
  const {directory} = load(input);
  return locked(directory, () => {
    const {run} = load(input);
    if (run.phase === 'complete') { assertSource(run); assertIntegration(run); return result(run, directory, {action: 'complete', build: run.build}); }
    assertApproval(run);
    if (!run.build) {
      const integration = path.join(directory, 'integration');
      const branch = `swarm/${run.id}/integration`;
      ensure(!fs.existsSync(integration) && git(run.repo, ['show-ref', '--verify', '--quiet', `refs/heads/${branch}`], {allowFailure: true}).status !== 0, 'Integration allocation already exists; reconcile it before retrying');
      git(run.repo, ['worktree', 'add', '-b', branch, integration, run.snapshot.head]);
      run.build = {integration, branch, head: run.snapshot.head, completed: [], pending: [], integrated: [], cycle: 0, review: null};
      run.phase = 'building'; save(directory, run);
    }
    assertIntegration(run);
    if (run.build.pending.length) {
      if (!run.build.pending.every(item => fs.existsSync(path.join(directory, 'patches', `${item.key}.json`)))) return result(run, directory, {action: 'develop', integration: run.build.integration, pending: run.build.pending.map(item => ({...item, task: run.plan.tasks.find(t => t.id === item.taskId)})), repairs: run.build.repairs || []});
      integrate(run, directory);
    }
    if (run.build.review) {
      if (!run.finalRoles.every(role => fs.existsSync(path.join(directory, 'reports', `final-${role}-${run.build.head}-${run.build.cycle}.json`)))) return result(run, directory, {action: 'review', integration: run.build.integration, head: run.build.head, cycle: run.build.cycle, plan: run.plan, checks: run.build.review.checks, reviewRoles: run.finalRoles});
      const reports = run.finalRoles.map(role => validateReview(readJson(path.join(directory, 'reports', `final-${role}-${run.build.head}-${run.build.cycle}.json`)), run.build.head));
      const material = reports.flatMap(r => r.findings).filter(f => f.severity !== 'P2' && f.confidence !== 'unverified');
      if (reports.every(r => r.verdict === 'ok') && material.length === 0) {
        run.phase = 'complete'; run.build.review = {head: run.build.head, verdict: 'ok', reports: run.finalRoles.map(role => path.join(directory, 'reports', `final-${role}-${run.build.head}-${run.build.cycle}.json`))};
        save(directory, run); return result(run, directory, {action: 'complete', build: run.build});
      }
      ensure(material.length > 0, 'Independent review is blocked without a scoped fix; parent decision required');
      ensure(run.build.cycle < run.config.maxRepairCycles, 'Repair limit reached; preserve the checkpoint for manual decision');
      const repairs = [...new Set(material.map(f => {
        const task = run.plan.tasks.find(t => t.id === f.taskId && t.paths.some(p => beneath(relative(f.path), p)));
        ensure(task, 'Finding needs edits outside approved task scope; obtain a new plan approval'); return task.id;
      }))];
      run.build.completed = run.build.completed.filter(id => !repairs.includes(id));
      run.build.repairs = material; run.build.cycle++; run.build.review = null;
    }
    const ready = readyTasks(run.plan.tasks, run.build.completed, run.config.maxConcurrent);
    if (ready.length) {
      ensure(run.admissions + ready.length <= run.config.maxAgents, 'Agent budget exhausted; preserve the checkpoint');
      run.build.pending = ready.map(task => ({taskId: task.id, key: `${task.id}-r${run.build.cycle}-${run.build.head.slice(0, 12)}`, base: run.build.head}));
      run.admissions += ready.length; run.phase = 'building'; save(directory, run);
      return result(run, directory, {action: 'develop', integration: run.build.integration, pending: run.build.pending.map(item => ({...item, task: run.plan.tasks.find(t => t.id === item.taskId)})), repairs: run.build.repairs || []});
    }
    ensure(run.build.completed.length === run.plan.tasks.length, 'No ready task; dependency/checkpoint state needs inspection');
    ensure(run.admissions + run.finalRoles.length <= run.config.maxAgents, 'Agent budget exhausted before independent review');
    const beforeChecks = snapshot(run.build.integration);
    const checks = runChecks(run.build.integration, run.plan.tasks.flatMap(t => t.verify), path.join(directory, 'checks', `integrated-${run.build.head}`));
    ensure(snapshot(run.build.integration).digest === beforeChecks.digest, 'Integrated checks mutated source; preserve it for inspection');
    run.admissions += run.finalRoles.length; run.build.review = {head: run.build.head, checks}; run.phase = 'verifying'; save(directory, run);
    return result(run, directory, {action: 'review', integration: run.build.integration, head: run.build.head, cycle: run.build.cycle, plan: run.plan, checks, reviewRoles: run.finalRoles});
  });
}
export function checkpoint(input) {
  const {run, directory} = load(input); assertSource(run);
  return result(run, directory, {goal: run.goal, plan: run.plan, planHash: run.planHash, build: run.build, approval: run.approval ? {at: run.approval.at, planHash: run.approval.planHash} : null});
}
export function wireResult(action, value) {
  // runs.host exposes only a 4-KiB stdout preview to scripts. Keep control data
  // below that bound; full plans/reviews/receipts are durable file artifacts.
  const out = {id: value.id, runDirectory: value.runDirectory, phase: value.phase, source: value.source, admissions: value.admissions, completed: value.completed, config: value.config && {maxConcurrent: value.config.maxConcurrent, maxAgents: value.config.maxAgents, maxRepairCycles: value.config.maxRepairCycles}};
  const planPath = value.runDirectory && path.join(value.runDirectory, 'plan.json');
  if (action === 'admit') out.slots = value.slots.map(slot => ({name: slot.name, cached: Boolean(slot.cached), reportPath: path.join(value.runDirectory, 'reports', slot.name + '.json')}));
  if (action === 'collect') Object.assign(out, {planPath, planHash: value.planHash, taskCount: value.plan.tasks.length, taskIds: value.plan.tasks.map(task => task.id), next: value.next});
  if (action === 'advance') {
    out.action = value.action;
    if (value.action === 'develop') {
      Object.assign(out, {integration: value.integration, head: value.pending[0].base, planPath, pending: value.pending.map(item => ({taskId: item.taskId, key: item.key, base: item.base, title: item.task.title.slice(0, 100)}))});
      if (value.repairs?.length) { out.repairsPath = path.join(value.runDirectory, 'reports', `repairs-${value.admissions}.json`); writeJson(out.repairsPath, value.repairs); }
    } else if (value.action === 'review') {
      const checksPath = path.join(value.runDirectory, 'checks', `integrated-${value.head}`, 'summary.json'); writeJson(checksPath, value.checks);
      Object.assign(out, {integration: value.integration, head: value.head, cycle: value.cycle, reviewRoles: value.reviewRoles, planPath, checksPath});
    } else if (value.action === 'complete') {
      const resultPath = path.join(value.runDirectory, 'result.json'); writeJson(resultPath, value);
      Object.assign(out, {integration: value.build.integration, branch: value.build.branch, head: value.build.head, resultPath});
    }
  }
  if (action === 'task-check') return {taskId: value.taskId, key: value.key, verified: true};
  ensure(Buffer.byteLength(JSON.stringify(out)) < 3500, 'Controller metadata exceeds native preview bound; scope paths/config more narrowly');
  return out;
}
export function execute(action, input, cwd) {
  ensure(['prepare', 'admit', 'collect', 'advance', 'task-check', 'status'].includes(action), 'Unsupported controller action; approval is interactive-only');
  return wireResult(action, ({prepare, admit, collect, advance, 'task-check': value => taskCheck(value, cwd), status: checkpoint})[action](input));
}
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  try { const value = execute(process.argv[2], JSON.parse(process.argv[3] || '{}')); process.stdout.write(JSON.stringify(value) + '\n'); }
  catch (error) { console.error(`badwater-swarm: ${error.message}`); process.exitCode = 1; }
}
