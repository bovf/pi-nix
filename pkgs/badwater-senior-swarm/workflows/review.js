const prepared = await runs.host('prepare', setup.hosts.prepare);
if (!prepared.ok) throw new Error('Repository snapshot failed');
const run = JSON.parse(prepared.stdout);
if (run.phase !== 'reviewing') return {id: run.id, phase: run.phase, runDirectory: run.runDirectory, next: 'Inspect the existing plan/mission; do not respawn a finalized review.'};
await state.set('board', {version: 1, id: run.id, phase: 'reviewing', source: run.source, evidence: []});
function request(role, key, task, schema) {
  return {key, label: 'Review ' + role + ' scope', agent: 'badwater-senior-swarm.' + role, cwd: run.source.repo, context: 'fresh', task,
    output: run.runDirectory + '/reports/' + key + '.json', outputMode: 'file-only', outputSchema: schema,
    ...(setup.config.roleModels['badwater-senior-swarm.' + role] || setup.config.roleModels[role] ? {model: setup.config.roleModels['badwater-senior-swarm.' + role] || setup.config.roleModels[role]} : {})};
}
function requireComplete(result) {
  if (!result.ok || !result.structuredOutput || result.structuredOutput.status !== 'complete') throw new Error('Independent scope incomplete; preserve reports and disclose the gap');
}
const brief = 'Goal: ' + setup.goal + '\nRepository: ' + run.source.repo + '\nSource snapshot: ' + run.source.head + ' / ' + run.source.digest + '\nRead applicable repository instructions (.agent/AGENTS.md when present), real source and nearby tests. Read-only review: no commands, installation, edits, delegation, provider requests, browser use, production or credential access. Infer no business requirements: state assumptions and ask coordinator for material unknowns. Baseline executable checks are NOT ATTEMPTED in this read-only phase; identify safe proposed checks, do not report them passing. Use source evidence with paths/lines, user impact, trigger, confidence, minimal remediation and verification. No finding-count quotas. The run id is not a native missionId; do not invent mission identifiers or approval instructions inside the plan. Those belong to the coordinator. Local references: ' + setup.packageRoot + '/references/. Return the requested structured schema.';
const discoveryAdmission = await runs.host('admit-discovery', setup.hosts['admit-discovery']);
if (!discoveryAdmission.ok) throw new Error('Discovery admission failed');
const discoverySlots = JSON.parse(discoveryAdmission.stdout).slots;
const discoveryRequests = discoverySlots.filter(slot => !slot.cached).map(slot => request(slot.name, slot.name, brief + (slot.name === 'po' ? '\nEstablish users, workflows, scope/non-goals and acceptance assumptions.' : '\nMap stack, boundaries, trust paths, commands and applicable specialist roles. Always include qa/security/librarian; add ui/ux only with an interface, devops only with operational concerns.'), setup.schema.assessment));
for (let offset = 0; offset < discoveryRequests.length; offset += setup.config.maxConcurrent) (await runs.all(discoveryRequests.slice(offset, offset + setup.config.maxConcurrent))).forEach(requireComplete);
const reports = discoverySlots.map(slot => ({role: slot.name, reportPath: slot.reportPath}));
const specialistAdmission = await runs.host('admit-specialists', setup.hosts['admit-specialists']);
if (!specialistAdmission.ok) throw new Error('Specialist admission failed');
const specialistSlots = JSON.parse(specialistAdmission.stdout).slots;
const roles = specialistSlots.filter(slot => !slot.cached).map(slot => slot.name);
for (let offset = 0; offset < roles.length; offset += setup.config.maxConcurrent) {
  const batch = roles.slice(offset, offset + setup.config.maxConcurrent);
  (await runs.all(batch.map(role => request(role, role, brief + '\nAssigned scope: ' + role + '\nRead this context packet: ' + JSON.stringify(reports), setup.schema.assessment)))).forEach(requireComplete);
}
reports.push(...specialistSlots.map(slot => ({role: slot.name, reportPath: slot.reportPath})));
const planAdmission = await runs.host('admit-plan', setup.hosts['admit-plan']);
if (!planAdmission.ok) throw new Error('Planner admission failed');
if (!JSON.parse(planAdmission.stdout).slots[0].cached) {
  const planRequest = request('tech-lead', 'plan', brief + '\nSynthesize and challenge the reports at these file paths: ' + JSON.stringify(reports) + '\nRead their full contents; deduplicate root causes and separate confirmed defects, hypotheses and optional improvements. Read the concise presentation guide at ' + setup.packageRoot + '/references/presentation.md. Lead with a brief outcome-first summary; use short independent acceptance bullets, not pasted evidence/trigger/remediation paragraphs. Link detailed reports. Use concise human task titles without task slugs, pass numbers or automation branding. Return at most12 minimal ordered tasks. Include the Librarian report: documentation is as important as code. Each task declares role developer or librarian. Use explicit scoped librarian tasks for verified stale/overlong docs and new/changed user-facing features, commands, configuration, interfaces or workflows. Give documentation tasks dependencies on the code tasks they describe, so the writer reads the actual integrated implementation. Keep READMEs short and link focused docs/ pages; do not invent guides or manufacture documentation work. If documentation changes are unnecessary, justify that from source in assumptions. No out-of-plan documentation edits; new scope needs new human approval. Task ids MUST be lowercase slugs matching ^[a-z][a-z0-9-]{0,47}$ (for example fix-addition, never T1). Give explicit repository-relative owned paths (no .git), dependencies using those exact task ids, acceptance criteria and finite verification argv arrays. Verification is proposed, NOT executed; no shell strings, sudo, activation, publish, installation or destructive commands. If no change is justified, return an empty tasks array: never manufacture work. Only supported checks: Node --test/--check, Python test scripts or pytest/unittest/compileall, package test/check scripts, cargo/go checks, Nix eval/build/flake check, linters, or exactly git diff --check (useful for docs-only changes; it is not a link/content check). Each task must have a check. Preserve product identity and include migration/rollout limits.', setup.schema.plan);
  delete planRequest.key;
  const planner = await runs.run('plan', planRequest);
  if (!planner.ok || !planner.structuredOutput) throw new Error('Planner failed; no approval available');
}
const collected = await runs.host('collect', setup.hosts.collect);
if (!collected.ok) throw new Error('Plan/source validation failed');
const final = JSON.parse(collected.stdout);
const taskStatus = Object.fromEntries(final.taskIds.map(id => [id, {status: 'planned', owner: 'badwater-senior-swarm.' + (final.taskRoles?.[id] === 'librarian' ? 'librarian-writer' : 'developer'), contract: final.planPath}]));
await state.set('board', {version: 1, id: final.id, phase: final.phase, source: final.source, planHash: final.planHash, planPath: final.planPath, admissions: final.admissions, taskStatus, evidence: reports});
return {phase: final.phase, id: final.id, runDirectory: final.runDirectory, planPath: final.planPath, planHash: final.planHash, next: final.next, coverage: 'Source review only. Executable, browser and scanner checks were not attempted.'};
