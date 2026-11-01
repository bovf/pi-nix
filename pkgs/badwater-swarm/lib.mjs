import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

export const ROOT = path.dirname(fileURLToPath(import.meta.url));
export const ROLES = ['po', 'tech-lead', 'ux', 'ui', 'qa', 'security', 'devops'];
export const READ_TOOLS = ['read', 'grep', 'find', 'ls', 'contact_supervisor'];
export const hash = value => crypto.createHash('sha256').update(typeof value === 'string' || Buffer.isBuffer(value) ? value : JSON.stringify(value)).digest('hex');
export function ensure(condition, message) { if (!condition) throw new Error(message); }
export function loadPaths() {
  const file = path.join(ROOT, 'paths.json');
  return fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : {node: process.execPath, git: 'git', shell: 'bash', browser: null};
}
export function settings(value = {}) {
  ensure(value && typeof value === 'object' && !Array.isArray(value), 'badwaterSwarm settings must be an object');
  const out = {maxConcurrent: 6, maxAgents: 32, maxRepairCycles: 2, roleModels: {}, browserCommand: null, ...value};
  for (const [key, min, max] of [['maxConcurrent', 1, 6], ['maxAgents', 1, 64], ['maxRepairCycles', 0, 2]]) ensure(Number.isInteger(out[key]) && out[key] >= min && out[key] <= max, `Invalid ${key}`);
  ensure(out.roleModels && typeof out.roleModels === 'object' && !Array.isArray(out.roleModels), 'Invalid roleModels');
  for (const [role, model] of Object.entries(out.roleModels)) ensure([...ROLES, 'developer'].includes(role.replace(/^swarm\./, '')) && typeof model === 'string' && model.length > 0 && model.length <= 200, 'Invalid role model selection');
  ensure(out.browserCommand === null || (typeof out.browserCommand === 'string' && path.isAbsolute(out.browserCommand)), 'browserCommand must be an absolute managed executable');
  return out;
}
export function identifier(value) { ensure(typeof value === 'string' && /^[a-z][a-z0-9-]{0,47}$/.test(value), 'id must be a short lowercase slug'); return value; }
export function relative(value) {
  ensure(typeof value === 'string' && value.length > 0 && value.length < 512 && !/[\x00-\x1f\\]/.test(value) && !path.isAbsolute(value), 'Invalid repository-relative path');
  const pieces = value.replace(/\/$/, '').split('/');
  ensure(pieces.every(x => x && x !== '.' && x !== '..') && !pieces.includes('.git'), 'Path escapes its repository boundary');
  return value.replace(/\/$/, '');
}
export function beneath(file, scope) { return file === scope || file.startsWith(scope + '/'); }
export function privateDirectory(directory) {
  const absolute = path.resolve(directory);
  for (let p = absolute; p !== path.dirname(p); p = path.dirname(p)) {
    let info; try { info = fs.lstatSync(p); } catch (error) { if (error.code !== 'ENOENT') throw error; }
    if (info) ensure(!info.isSymbolicLink(), 'Refusing symlinked swarm storage');
  }
  fs.mkdirSync(absolute, {recursive: true, mode: 0o700});
  const info = fs.statSync(absolute);
  ensure(!process.getuid || info.uid === process.getuid(), 'Swarm storage is not owned by this user');
  fs.chmodSync(absolute, 0o700);
  return absolute;
}
export function readJson(file) {
  const info = fs.lstatSync(file);
  ensure(info.isFile() && !info.isSymbolicLink() && info.nlink === 1 && info.size <= 256 * 1024, 'Invalid swarm JSON artifact');
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}
export function writeJson(file, value) {
  const bytes = JSON.stringify(value, null, 2) + '\n';
  ensure(Buffer.byteLength(bytes) <= 256 * 1024, 'Swarm metadata exceeds 256 KiB');
  privateDirectory(path.dirname(file));
  let existing; try { existing = fs.lstatSync(file); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  if (existing) readJson(file);
  const temp = path.join(path.dirname(file), '.' + path.basename(file) + '-' + crypto.randomUUID());
  const fd = fs.openSync(temp, 'wx', 0o600);
  try { fs.writeFileSync(fd, bytes); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
  try {
    fs.renameSync(temp, file);
    const parent = fs.openSync(path.dirname(file), 'r');
    try { fs.fsyncSync(parent); } finally { fs.closeSync(parent); }
  } finally { if (fs.existsSync(temp)) fs.unlinkSync(temp); }
}
export function command(argv, cwd, {env = {}, timeout = 120000, input, allowFailure = false} = {}) {
  ensure(Array.isArray(argv) && argv.length && argv.every(x => typeof x === 'string' && !x.includes('\0')), 'Invalid command arguments');
  const childEnv = {...process.env, ...env};
  // Node's outer test-runner marker otherwise makes nested --test checks skip execution.
  delete childEnv.NODE_TEST_CONTEXT;
  const result = spawnSync(argv[0], argv.slice(1), {cwd, env: childEnv, encoding: 'utf8', timeout, input, maxBuffer: 16 * 1024 * 1024});
  if (!allowFailure) ensure(!result.error && result.status === 0, `Command failed (${path.basename(argv[0])}, exit ${result.status ?? 'unavailable'}); inspect the private command receipt`);
  return {status: result.status, signal: result.signal, stdout: result.stdout || '', stderr: result.stderr || '', error: result.error?.code || null};
}
export function git(cwd, args, options) { return command([loadPaths().git, '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false', ...args], cwd, options); }
export function repository(cwd) { return fs.realpathSync(git(cwd, ['rev-parse', '--show-toplevel']).stdout.trim()); }
export function snapshot(cwd) {
  const repo = repository(cwd);
  const head = git(repo, ['rev-parse', 'HEAD']).stdout.trim();
  const branch = git(repo, ['symbolic-ref', '--quiet', 'HEAD'], {allowFailure: true}).stdout.trim() || null;
  const status = git(repo, ['status', '--porcelain=v1', '-z', '--untracked-files=all']).stdout;
  const digest = crypto.createHash('sha256').update(head).update(branch || 'DETACHED').update(status).update(git(repo, ['diff', '--binary', '--no-ext-diff', '--no-textconv', 'HEAD', '--']).stdout);
  const untracked = git(repo, ['ls-files', '--others', '--exclude-standard', '-z']).stdout.split('\0').filter(Boolean);
  for (const file of untracked.sort()) {
    relative(file);
    const target = path.join(repo, file), info = fs.lstatSync(target);
    ensure(info.isSymbolicLink() || (info.isFile() && info.size <= 50 * 1024 * 1024), 'Untracked snapshot entry is unsupported or too large; scope the checkout first');
    digest.update(file).update(String(info.mode)).update(info.isSymbolicLink() ? fs.readlinkSync(target) : fs.readFileSync(target));
  }
  return {repo, head, branch, digest: digest.digest('hex'), clean: status.length === 0};
}
export function runDirectory(repo, id, root) {
  identifier(id);
  const base = root || path.join(process.env.XDG_STATE_HOME || path.join(os.homedir(), '.local/state'), 'badwater-swarm');
  ensure(path.isAbsolute(base) && !beneath(path.resolve(base), repository(repo)), 'Swarm state must be outside the source checkout');
  return path.join(base, hash(repository(repo)).slice(0, 16), id);
}
export function locked(directory, fn) {
  privateDirectory(directory);
  const lock = path.join(directory, '.controller-lock');
  try { fs.mkdirSync(lock, {mode: 0o700}); } catch { throw new Error('Swarm controller is active or has an unreconciled lock; inspect it, never run a second writer'); }
  fs.writeFileSync(path.join(lock, 'owner.json'), JSON.stringify({pid: process.pid, at: new Date().toISOString()}), {mode: 0o600});
  try { return fn(); } finally { fs.rmSync(lock, {recursive: true}); }
}
export function validateCheck(check) {
  ensure(check && Array.isArray(check.argv) && check.argv.length > 1 && check.argv.length <= 32 && check.argv.every(x => typeof x === 'string' && x.length > 0 && x.length <= 1024 && !/[\x00-\x1f]/.test(x)), 'Verification needs an argv array, not a shell string');
  const [exe, ...args] = check.argv;
  ensure(!exe.includes('/') && ['node', 'python3', 'pytest', 'npm', 'pnpm', 'yarn', 'cargo', 'go', 'nix', 'ruff', 'ty', 'statix', 'deadnix', 'shellcheck', 'bash'].includes(exe), 'Unsupported verification executable; choose a documented check');
  if (exe === 'bash') ensure(args[0] === '-n', 'Only Bash syntax checks are admitted');
  if (exe === 'node') ensure(args[0] === '--test' || args[0] === '--check', 'Only Node test/syntax checks are admitted');
  if (exe === 'python3') ensure((args[0] === '-m' && ['pytest', 'unittest', 'compileall'].includes(args[1])) || /^([^/]+\/)*test[-_][^/]+\.py$/.test(args[0]), 'Only Python test/syntax checks are admitted');
  if (['npm', 'pnpm', 'yarn'].includes(exe)) ensure(['test', 'run'].includes(args[0]) && (args[0] === 'test' || ['test', 'check', 'lint', 'typecheck', 'build'].includes(args[1])), 'Only package test/check scripts are admitted');
  if (exe === 'cargo') ensure(['test', 'check', 'clippy', 'fmt'].includes(args[0]), 'Only Cargo checks are admitted');
  if (exe === 'go') ensure(['test', 'vet', 'build'].includes(args[0]), 'Only Go checks are admitted');
  if (exe === 'nix') ensure(['eval', 'build', 'flake'].includes(args[0]) && (args[0] !== 'flake' || args[1] === 'check'), 'Only Nix evaluation/build/check is admitted');
  ensure(!args.some(x => /(^|[\/])(switch-to-configuration|nixos-rebuild|darwin-rebuild)$/.test(x)), 'Activation is not verification');
  const seconds = check.timeoutSeconds ?? 120;
  ensure(Number.isInteger(seconds) && seconds >= 1 && seconds <= 1800, 'Invalid verification deadline');
  return {argv: check.argv, timeoutSeconds: seconds};
}
export function validatePlan(plan) {
  ensure(plan && typeof plan === 'object' && typeof plan.summary === 'string' && plan.summary.length > 0, 'Plan needs a summary');
  ensure(Array.isArray(plan.acceptance) && plan.acceptance.length > 0 && plan.acceptance.length <= 20 && plan.acceptance.every(x => typeof x === 'string' && x.length > 0), 'Plan needs bounded acceptance criteria');
  ensure(Array.isArray(plan.tasks) && plan.tasks.length <= 12, 'Plan must contain at most12 scoped tasks; a clean review may need none');
  const ids = new Set();
  const tasks = plan.tasks.map(task => {
    const id = identifier(task.id); ensure(!ids.has(id), 'Duplicate task id'); ids.add(id);
    ensure(typeof task.title === 'string' && task.title.length > 0 && task.title.length <= 200, 'Task needs a short title');
    ensure(Array.isArray(task.paths) && task.paths.length > 0 && task.paths.length <= 20, 'Task needs explicit paths');
    ensure(Array.isArray(task.dependencies) && task.dependencies.every(x => typeof x === 'string'), 'Task dependencies must be an array');
    ensure(Array.isArray(task.criteria) && task.criteria.length > 0 && task.criteria.every(x => typeof x === 'string' && x.length > 0), 'Task needs acceptance criteria');
    ensure(Array.isArray(task.verify) && task.verify.length > 0 && task.verify.length <= 8, 'Task needs executable verification');
    return {id, title: task.title, paths: task.paths.map(relative), dependencies: task.dependencies, criteria: task.criteria, verify: task.verify.map(validateCheck)};
  });
  for (const task of tasks) ensure(task.dependencies.every(x => ids.has(x) && x !== task.id), 'Unknown/self task dependency');
  const done = new Set();
  while (done.size < tasks.length) {
    const ready = tasks.filter(t => !done.has(t.id) && t.dependencies.every(x => done.has(x)));
    ensure(ready.length > 0, 'Cyclic task dependencies'); ready.forEach(t => done.add(t.id));
  }
  return {summary: plan.summary, acceptance: plan.acceptance, tasks, assumptions: plan.assumptions || [], rollout: plan.rollout || 'Local integration branch only; publication and deployment require separate approval.'};
}
export function readyTasks(tasks, completed, concurrency) {
  const batch = [];
  for (const task of tasks) {
    if (completed.includes(task.id) || !task.dependencies.every(x => completed.includes(x))) continue;
    if (batch.some(other => task.paths.some(p => other.paths.some(q => beneath(p, q) || beneath(q, p))))) continue;
    batch.push(task); if (batch.length === concurrency) break;
  }
  return batch;
}
export function validateReview(report, expectedHead) {
  ensure(report && report.status === 'complete' && ['ok', 'blocked'].includes(report.verdict) && report.head === expectedHead && Array.isArray(report.findings), 'Missing, incomplete or stale independent review');
  for (const finding of report.findings) {
    ensure(['P0', 'P1', 'P2'].includes(finding.severity) && ['confirmed', 'supported', 'unverified'].includes(finding.confidence), 'Invalid review severity/confidence');
    ensure(['evidence', 'impact', 'trigger', 'remediation', 'verification'].every(k => typeof finding[k] === 'string' && finding[k].length > 0), 'Finding lacks actionable evidence');
    relative(finding.path);
  }
  if (report.verdict === 'ok') ensure(!report.findings.some(f => f.severity !== 'P2' && f.confidence !== 'unverified'), 'Review verdict contradicts material findings');
  return report;
}
export function quoted(value) { return "'" + value.replaceAll("'", "'\\''") + "'"; }
export const stringArray = {type: 'array', items: {type: 'string'}, maxItems: 20};
const finding = {type: 'object', properties: {severity: {enum: ['P0', 'P1', 'P2']}, confidence: {enum: ['confirmed', 'supported', 'unverified']}, path: {type: 'string'}, evidence: {type: 'string'}, impact: {type: 'string'}, trigger: {type: 'string'}, remediation: {type: 'string'}, verification: {type: 'string'}, taskId: {type: 'string', pattern: '^[a-z][a-z0-9-]{0,47}$'}}, required: ['severity', 'confidence', 'path', 'evidence', 'impact', 'trigger', 'remediation', 'verification'], additionalProperties: false};
export const ASSESSMENT_SCHEMA = {type: 'object', properties: {status: {enum: ['complete', 'blocked']}, summary: {type: 'string'}, assumptions: stringArray, coverage: stringArray, applicableRoles: {type: 'array', items: {enum: ROLES}, maxItems: 7}, findings: {type: 'array', items: finding, maxItems: 20}}, required: ['status', 'summary', 'coverage', 'applicableRoles', 'findings'], additionalProperties: false};
export const PLAN_SCHEMA = {type: 'object', properties: {summary: {type: 'string'}, acceptance: stringArray, assumptions: stringArray, rollout: {type: 'string'}, tasks: {type: 'array', minItems: 0, maxItems: 12, items: {type: 'object', properties: {id: {type: 'string', pattern: '^[a-z][a-z0-9-]{0,47}$'}, title: {type: 'string'}, paths: stringArray, dependencies: stringArray, criteria: stringArray, verify: {type: 'array', minItems: 1, maxItems: 8, items: {type: 'object', properties: {argv: {type: 'array', items: {type: 'string'}, minItems: 2, maxItems: 32}, timeoutSeconds: {type: 'integer', minimum: 1, maximum: 1800}}, required: ['argv', 'timeoutSeconds'], additionalProperties: false}}}, required: ['id', 'title', 'paths', 'dependencies', 'criteria', 'verify'], additionalProperties: false}}}, required: ['summary', 'acceptance', 'tasks', 'assumptions', 'rollout'], additionalProperties: false};
export const FINAL_REVIEW_SCHEMA = {type: 'object', properties: {status: {enum: ['complete', 'blocked']}, verdict: {enum: ['ok', 'blocked']}, head: {type: 'string'}, summary: {type: 'string'}, findings: {type: 'array', items: finding, maxItems: 20}}, required: ['status', 'verdict', 'head', 'summary', 'findings'], additionalProperties: false};
