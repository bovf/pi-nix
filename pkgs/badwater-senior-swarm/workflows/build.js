function quote(value) { return "'" + value.replaceAll("'", "'\\''") + "'"; }
function model(role) {
  const selected = setup.config.roleModels['badwater-senior-swarm.' + role] || setup.config.roleModels[role];
  return selected ? {model: selected} : {};
}
for (let index = 0; index < 32; index++) {
  const host = await runs.host('step-' + index, setup.hosts['step-' + index]);
  if (!host.ok) throw new Error('Controller blocked; inspect the private checkpoint and host-step receipt, do not drop isolation or approval');
  const step = JSON.parse(host.stdout);
  const board = await state.get('board') || {version: 1, id: step.id, taskStatus: {}};
  const taskStatus = board.taskStatus || {};
  (step.completed || []).forEach(id => { taskStatus[id] = {...(taskStatus[id] || {}), status: step.action === 'complete' ? 'completed' : 'integrated'}; });
  (step.pending || []).forEach(item => { taskStatus[item.taskId] = {...(taskStatus[item.taskId] || {}), status: 'running', owner: 'badwater-senior-swarm.' + (item.role === 'librarian' ? 'librarian-writer' : 'developer'), contract: step.planPath}; });
  await state.set('board', {...board, phase: step.phase, source: step.source, admissions: step.admissions, integration: step.integration, head: step.head || null, taskStatus, evidence: [step.checksPath || step.resultPath].filter(Boolean)});
  if (step.action === 'complete') return {phase: 'complete', id: step.id, runDirectory: step.runDirectory, integration: step.integration, branch: step.branch, head: step.head, resultPath: step.resultPath, authority: 'Local result only. No push, main merge, activation or deployment performed.'};
  if (step.action === 'develop') {
    const requests = step.pending.map(item => {
      const role = item.role || 'developer';
      const agent = role === 'librarian' ? 'librarian-writer' : 'developer';
      const gate = quote(setup.node) + ' ' + quote(setup.cli) + ' task-check ' + quote(JSON.stringify({...setup.input, key: item.key}));
      return {key: item.key, label: 'Implement ' + item.title, agent: 'badwater-senior-swarm.' + agent, context: 'fresh', cwd: step.integration, worktree: true, baseRef: 'HEAD',
        task: 'Read the complete approved plan at ' + step.planPath + '. Implement ONLY its task id ' + item.taskId + ' in your isolated worktree. Base: ' + item.base + '. Read applicable verified findings at ' + (step.repairsPath || '(none)') + '. Read repository instructions, source, callers and named tests. Preserve all other behavior. Own only that task\'s listed repository-relative paths. Do not stage/commit, modify .git, publish, install dependencies, activate/deploy, access secrets/production or delegate. Tests are the exact approved argv declarations. The host gate independently executes them and captures a scoped patch. If work escapes scope, stop and contact_supervisor. Do not write shared board or approval files. Return implemented or blocked with changed paths and limitations. For librarian tasks, read the actual integrated source and upstream writer handoffs, then document only the approved behavior and documentation scope; prefer a short README with focused linked docs/ pages. No speculative claims, duplicate manuals or code/config edits. For developer tasks, leave concise evidence of actual behavior/tests and documentation impacts for the Librarian, not unapproved extra files.',
        output: step.runDirectory + '/reports/' + role + '-' + item.key + '.json', outputMode: 'file-only',
        outputSchema: {type: 'object', properties: {status: {enum: ['implemented', 'blocked']}, summary: {type: 'string'}, changedFiles: {type: 'array', items: {type: 'string'}}, limitations: {type: 'array', items: {type: 'string'}}}, required: ['status', 'summary', 'changedFiles', 'limitations'], additionalProperties: false},
        acceptance: {level: 'verified', report: 'on', verify: [{id: 'approved-task', command: gate, timeoutMs: 1800000}], review: {required: false}}, ...model(role)};
    });
    const outcomes = await runs.all(requests);
    if (outcomes.some(item => !item.ok || item.structuredOutput?.status !== 'implemented')) throw new Error('Developer did not complete its approved task; preserve handoff and gate evidence');
  } else if (step.action === 'review') {
    for (let offset = 0; offset < step.reviewRoles.length; offset += step.config.maxConcurrent) {
      const batch = step.reviewRoles.slice(offset, offset + step.config.maxConcurrent);
      const outcomes = await runs.all(batch.map(role => ({key: 'final-' + role + '-' + step.head + '-' + step.cycle, label: 'Verify integrated ' + role, agent: 'badwater-senior-swarm.' + role, context: 'fresh', cwd: step.integration,
        task: 'Fresh independent final ' + role + ' review of the actual integrated checkout. Read the approved plan at ' + step.planPath + ' and actual host check summary at ' + step.checksPath + '; follow its individual private command receipts. Exact reviewed HEAD: ' + step.head + '. Test errors are not passes. Read-only: no edits, commands, delegation, browser/profile, production or credential access. Source review does not certify UI pixels, live services, hardware or external authorization. For UI/UX preserve incumbent design and record missing rendered evidence. For librarian, trace documentation claims/commands/configuration to the actual integrated source and approved changes; inspect links and navigation, stale/duplicated content, concise README/docs/ separation, relevant new-feature guidance and removed/renamed behavior. No invented guarantees, installation steps or exhaustive manuals; record checks not actually performed as gaps. Return complete with verdict ok only if no concrete material blockers remain, otherwise blocked. Findings require path, file/symbol/line evidence, impact, trigger, confidence, smallest remediation, verification and the lowercase approved taskId for any scoped fix. Do not invent defects or exhaustive coverage. Return the exact supplied head.',
        output: step.runDirectory + '/reports/final-' + role + '-' + step.head + '-' + step.cycle + '.json', outputMode: 'file-only', outputSchema: setup.schema.final, ...model(role)})));
      if (outcomes.some(item => !item.ok || item.structuredOutput?.status !== 'complete')) throw new Error('Independent verification incomplete; do not declare success');
    }
  } else throw new Error('Unsupported controller state');
}
throw new Error('Controller stage limit reached; preserve mission and checkpoint for an explicit continuation');
