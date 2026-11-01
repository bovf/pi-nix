---
name: badwater-senior-swarm
description: Coordinate an evidence-driven senior team for repository review or approved local implementation, with product, architecture, QA, security, DevOps, UI and UX specialists.
disable-model-invocation: true
license: MIT
---

# Badwater Senior Swarm

Use only when the operator explicitly invokes this skill or requests this team.
The parent is coordinator/Scrum master and final decision owner. A role is not a
standing instruction to spawn every specialist. No nested delegation, external
agent CLI, peer mesh or new daemon is needed. Read the installed pi-subagents
skill and actual API before orchestrating; never invent tool names.

## Commands

- `/skill:badwater-senior-swarm review <goal>`: source-backed independent review and a prioritized
  plan, with no application edits. Executable checks are proposed/not attempted
  by this phase; do not claim a green baseline. Discuss any missing business
  context and constraints with the operator.
- `/skill:badwater-senior-swarm build <goal>`: the same review/plan first, then STOP for human
  approval. It never starts developers merely because the goal says build.
- `/skill:badwater-senior-swarm resume <id>`: inspect the existing mission, reports and source
  snapshot first. A stopped native workflow can resume through the documented
  runtime controls; a new build workflow must attach the same missionId.
  Never reuse approval after source/plan drift. A changed Nix runtime package
  also requires a fresh reviewed run; do not migrate old approval silently.

## Before launching

Read applicable repo instructions, preserve its current branch/index/worktree,
record its revision and scope, and inspect the actual installed capabilities.
Query an existing Graphify map first only for navigation; check freshness and
read the source. A missing/stale graph is not a reason to run semantic extraction,
install anything, request credentials, or block source review. Reuse existing
LSP and documented check commands without changing providers or project policy.

Do not execute unfamiliar project scripts simply because AGENTS.md names them.
Tests, linters and builds execute repository code and can have side effects.
Keep production, deployment, credential operations, network scanning, system/home
activation and package publication outside this workflow. Tool filters and Git
worktrees are NOT operating-system isolation. Use an approved container/sandbox
for untrusted code; do not silently grant it host files, sockets or credentials.

Choose a new lowercase run id (up to48 chars) and a specific goal. Enable the
native subagent tools if their loader is available. Launch exactly one top-level
async workflow for the current phase, children only inside that workflow:

```text
subagent({
  workflow: "badwater-senior-swarm.review",
  args: {id: "review-auth-flow", goal: "Review auth and plan bounded improvements"},
  async: true,
  options: {mission: {title: "Review auth flow"}}
})
```

These are extension-registered named resources, not raw scripts. Do not pass
workflow-capacity overrides to named resources; the package batches at most six
children and durably admits each logical review lane before dispatch, reuses completed
source-bound reports on continuation, and maintains its cumulative admission cap. The package
uses native keyed runs, mission state and actual host verification receipts.
No MCP connection or provider request is required merely to register it.

Native completion wakes the parent. Do not sleep, poll or call bg_wait for
ordinary async children. Continue safe independent work or return control.
If launch/runtime/tool setup fails, report exact run/worktree state and inspect
partial changes before one same-protocol retry. Never switch silently to pi -ne,
another provider, external agent CLI or unisolated writing.

## Review and approval

The resource runs PO/BPO and technical discovery, then QA/security and only
applicable UI/UX/DevOps assessments, then a fresh synthesis. Each report separates
severity/confidence and gives source/runtime evidence, trigger, impact, smallest
correction and regression criteria. No fabricated findings or implicit product
requirements. Scope, priority and disposition remain parent decisions.

The workflow returns `planPath`/`resultPath` pointers, not inline reports. Read
those full artifacts before summarizing the plan, exact verification argv, scope
and coverage gaps to the user. Native host stdout previews are intentionally
small; never interpret a truncated preview as a complete JSON report.
The private runDirectory contains source/plan digests and reports; native mission
state is the task-board index. Preserve this missionId for the build phase and
record an approval decision as waiting when appropriate. Do not call mission
completion a delivered implementation: review stops at awaiting-approval.

The human must run `/badwater-senior-swarm-approve <runDirectory>` and confirm the exact plan in
Pi's read-only scrollable reader, then its separate Cancel-default confirmation.
Use arrows/Page Up/Page Down/Home/End to read; Enter continues, Tab selects the
final action, and Esc cancels. RPC uses a complete private review artifact and
compact Cancel-first selection. Opening the reader is not approval; never select
on the human's behalf. Headless/model-authored approval is refused by the command. Approval covers isolated developer worktrees, exact proposed checks,
and local integration-branch checkpoint commits only. It does not cover push,
main merge, deployments, credential use or production access. Declining changes
no source or approval; read-only review artifacts may remain. Dirty source must
be resolved by the user, never stashed/reset by us.

After confirmed approval, launch the next phase with the same id and mission:

```text
subagent({
  workflow: "badwater-senior-swarm.build",
  args: {id: "review-auth-flow"},
  async: true,
  options: {missionId: "<existing mission id>"}
})
```

The host checks exact source/plan approval before allocating an integration
worktree. Developers own disjoint ready tasks in managed worktrees. Host gates
execute exact approved checks, reject out-of-scope/no-change patches, and capture
scoped evidence. Integration is serial into a dedicated `badwater-senior-swarm/<id>/integration`
branch, never into the caller's working branch. Integrated checks and fresh
QA/security (plus applicable UI/UX) follow. At most two scoped repair cycles;
unknown/out-of-scope fixes, budget exhaustion or infrastructure errors preserve
a checkpoint instead of broadening authority. Child prose alone is not success.

Default limits: six concurrent children,32 logical admissions across both phases,
two repair cycles. Limits are scheduling caps, not hard currency guarantees.
Existing roleModels override only named roles; absent roles inherit the current
parent model. Do not change authentication, default provider or models to make
a failed launch pass. Native resumes can reuse children; every decision and
review remains tied to its recorded source/plan and integrated head.

## Specialist capabilities

Use only the relevant curated local references under `../../references/` from
this skill directory: Superpowers engineering, Trail-of-Bits security,
Impeccable UI/UX and Vercel web/React. They retain source pins/licenses. They do
not authorize their original plugin agents, global bootstraps, runtime installers,
file-writing commands or nested workflow. Existing Ponytail guidance still
favors minimal fixes, not compulsory TDD ceremony for trivial changes.

Context7, when configured, uses Pi builtin MCP only. The operator signs in via
`/mcp` or `pi mcp login context7`; credentials stay outside Nix. Query package
names, versions and documentation topics—not private source. Missing docs or
OAuth is a reported capability gap, not permission to install another MCP owner.

For a rendered review, obtain an approved local test URL/environment and consent
for screenshots sent to the model. Check the active model's declared visual
capability before visual claims. The coordinator alone owns the browser session.
Use the configured absolute `browserCommand` (badwater-senior-swarm-browser) with `--help` first.
It launches a fresh managed Playwright profile, never a personal CDP profile;
run axe plus desktop/narrow screenshots on synthetic or explicitly authorized
test data. Do not claim visual, keyboard or assistive-technology acceptance from
axe alone. Save evidence in the private run artifacts and give only relevant
redacted evidence to reviewers. Do not run the helper against production or
add network origins without approval. No browser launches on Pi startup.

Scanners are supplementary, opt-in evidence: use existing project checks first,
then applicable installed Gitleaks/Semgrep/OSV/Trivy/Go/Nix tools. Inspect commands,
local rules, data sharing, network use and exit semantics first. Never run a
mutating updater/autofix or report an unavailable/failed scanner as clean. Nix
locks are not automatically covered by npm/Go vulnerability tools. Known legacy
scan-app failure handling is not a sufficient completion gate.

## Handoff

Give the actual integrated branch/head and artifact/report/command receipt paths,
verification outcomes (passed/findings/failed/unavailable/not attempted), remaining
risks, and next manual action. Runtime reports are private local artifacts, not
public upload consent. Native debug artifacts can expire; the package's durable
runDirectory is retained until the operator explicitly removes it. Do not delete
worktrees or artifacts automatically at handoff. Close the mission only when the
requested delivery and its explicit verification are actually complete.
