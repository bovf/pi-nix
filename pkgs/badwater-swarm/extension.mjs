import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {pathToFileURL} from 'node:url';
import {ROOT, ROLES, ensure, settings, identifier, hash, quoted, repository, ASSESSMENT_SCHEMA, PLAN_SCHEMA, FINAL_REVIEW_SCHEMA} from './lib.mjs';
import {approvalDetails, approve, revoke} from './cli.mjs';

export function resolveResource(mode, args, context) {
  ensure(args && typeof args === 'object' && !Array.isArray(args), 'Workflow arguments must be an object');
  ensure(Object.keys(args).every(key => (mode === 'review' ? ['id', 'goal'] : ['id']).includes(key)), 'Unexpected workflow argument');
  identifier(args.id);
  if (mode === 'review') ensure(typeof args.goal === 'string' && args.goal.trim() && args.goal.length <= 4000, 'Review requires a bounded goal');
  const input = {repo: context.repo, id: args.id, stateRoot: context.stateRoot};
  const command = (action, value = input) => `${quoted(context.paths.node)} ${quoted(path.join(ROOT, 'cli.mjs'))} ${quoted(action)} ${quoted(JSON.stringify(value))}`;
  const setup = {input, goal: args.goal, config: context.config, packageRoot: ROOT, schema: {assessment: ASSESSMENT_SCHEMA, plan: PLAN_SCHEMA, final: FINAL_REVIEW_SCHEMA}, cli: path.join(ROOT, 'cli.mjs'), node: context.paths.node};
  const grants = mode === 'review' ? [
    {key: 'prepare', command: command('prepare', {...input, goal: args.goal, config: context.config})},
    ...['discovery', 'specialists', 'plan'].map(stage => ({key: 'admit-' + stage, command: command('admit', {...input, stage})})),
    {key: 'collect', command: command('collect')},
  ] : Array.from({length: 32}, (_, i) => ({key: `step-${i}`, command: command('advance')}));
  setup.hosts = Object.fromEntries(grants.map(grant => [grant.key, {kind: 'command', command: grant.command, timeoutMs: mode === 'review' ? 120000 : 1800000}]));
  return {script: `const setup = ${JSON.stringify(setup)};\n${context.scripts[mode]}`, hostCommands: grants};
}
export default async function swarm(pi) {
  const file = path.join(ROOT, 'paths.json');
  ensure(fs.existsSync(file), 'badwater-swarm needs the Nix-generated paths.json; do not install the source package imperatively');
  const paths = JSON.parse(fs.readFileSync(file, 'utf8'));
  // Native subagent host-step cleanup needs ps, even from a minimal Nix shell.
  if (paths.runtimePath) process.env.PATH = [...new Set((paths.runtimePath + path.delimiter + (process.env.PATH || '')).split(path.delimiter).filter(Boolean))].join(path.delimiter);
  const {SettingsManager} = await import(pathToFileURL(path.join(paths.pi, 'dist/index.js')).href);
  const {registerWorkflowResource} = await import(pathToFileURL(path.join(paths.subagents, 'src/api/workflow-resources.js')).href);
  const scripts = Object.fromEntries(['review', 'build'].map(mode => [mode, fs.readFileSync(path.join(ROOT, 'workflows', `${mode}.js`), 'utf8')]));
  let registrations = [];
  const dispose = () => { registrations.forEach(x => x.dispose()); registrations = []; };
  pi.on('session_start', (_event, ctx) => {
    dispose();
    const config = settings({browserCommand: paths.browser || null, ...(SettingsManager.create(ctx.cwd).getSettings().badwaterSwarm || {})});
    let repo; try { repo = repository(ctx.cwd); } catch { return; }
    const context = {repo, stateRoot: path.resolve(process.env.XDG_STATE_HOME || path.join(os.homedir(), '.local/state'), 'badwater-swarm'), paths, config, scripts};
    try {
      for (const mode of ['review', 'build']) registrations.push(registerWorkflowResource({sessionId: ctx.sessionManager.getSessionId(), definition: {name: `badwater-swarm.${mode}`, version: 1, resolve(args) { try { return resolveResource(mode, args, context); } catch (error) { return {error: error.message}; } }}}));
    } catch (error) { dispose(); throw error; }
  });
  pi.on('session_shutdown', dispose);
  pi.registerCommand('swarm-approve', {
    description: 'Inspect and approve the exact reviewed swarm plan for local isolated implementation',
    handler: async (args, ctx) => {
      ensure(ctx.hasUI, 'Swarm approval requires interactive human confirmation; headless approval is refused');
      const directory = path.resolve(args.trim());
      const run = approvalDetails(directory);
      ensure(repository(ctx.cwd) === run.repo, 'Approve from the reviewed source repository');
      const commands = run.plan.tasks.flatMap(t => t.verify.map(check => `${t.id}: ${JSON.stringify(check.argv)} (${check.timeoutSeconds}s)`));
      const text = [`Goal: ${run.goal}`, `Source: ${run.snapshot.head}`, `Plan SHA-256: ${run.planHash}`, run.plan.summary, ...run.plan.tasks.map(t => `${t.id}: ${t.title}\n  Paths: ${t.paths.join(', ')}\n  Acceptance: ${t.criteria.join('; ')}`), 'Exact verification commands (these execute repository code):', ...commands, 'Authorize isolated developer worktrees, serial integration and local checkpoint commits on a dedicated swarm branch. Your source branch is not edited. No push, main merge, activation, deployment, credentials or production access. Worktrees/tool filters are not an OS sandbox.'].join('\n\n');
      if (!(await ctx.ui.confirm('Approve this exact swarm plan?', text))) { ctx.ui.notify('Swarm plan remains unapproved.', 'info'); return; }
      const approved = approve(directory, {confirmed: true, sessionId: ctx.sessionManager.getSessionId(), planHash: run.planHash, sourceDigest: run.snapshot.digest});
      ctx.ui.notify(`Approved ${approved.id}; continuing through the parent coordinator.`, 'info');
      pi.sendUserMessage(`The human explicitly approved swarm ${approved.id} (plan ${run.planHash}). Inspect its existing mission and continue the local badwater-swarm.build phase with args {id:${JSON.stringify(approved.id)}} and the same missionId. Publishing, main merges, activation and deployment remain unauthorized.`, {deliverAs: 'followUp'});
    },
  });
  pi.registerCommand('swarm-status', {
    description: 'Read a swarm checkpoint without launching or resuming agents',
    handler: async (args, ctx) => {
      const run = JSON.parse(fs.readFileSync(path.join(path.resolve(args.trim()), 'run.json'), 'utf8'));
      ctx.ui.notify(`${run.id}: ${run.phase}; ${run.admissions}/${run.config.maxAgents} admissions; integration ${run.build?.head || 'not started'}.`, 'info');
    },
  });
  pi.registerCommand('swarm-revoke', {
    description: 'Revoke an idle swarm approval without deleting artifacts or worktrees',
    handler: async (args, ctx) => { ensure(ctx.hasUI && await ctx.ui.confirm('Revoke swarm approval?', 'Stop the native workflow and its children first. This revokes future gates/admission but cannot undo edits or cancel an in-flight command. No artifacts or worktrees will be deleted.'), 'Revocation not confirmed'); revoke(path.resolve(args.trim())); ctx.ui.notify('Swarm approval revoked.', 'info'); },
  });
}
