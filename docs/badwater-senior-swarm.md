# Badwater Senior Swarm

A Nix-managed Pi package, not another agent daemon. Home Manager integration is
owned by badwater-ai; pl-badwater initially opts in Heavy/Spy only. Package/build
and reference/browser details are in [badwater-senior-swarm-packaging.md](badwater-senior-swarm-packaging.md).

## Operator interface

After an operator-approved Home Manager activation and Pi restart:

```text
/skill:badwater-senior-swarm review this repository and plan security/correctness improvements
/skill:badwater-senior-swarm build <a bounded outcome>
/skill:badwater-senior-swarm resume <existing run id>
```

Both review and build requests first produce a source-backed plan. They do not
run application checks or edit application source during review. The parent
reads the full plan, exact proposed verification argv and coverage gaps, then
stops. The operator runs `/badwater-senior-swarm-approve <runDirectory>` and confirms that exact
plan in a bounded, read-only terminal viewer, then an explicit confirmation.
Headless approval fails closed; changed source,
branch, plan or Nix runtime package requires fresh review/confirmation. The
command queues continuation through the parent, not an independent writer.

`/badwater-senior-swarm-status <runDirectory>` reads status without launching anything.
`/badwater-senior-swarm-revoke <runDirectory>` revokes future admission/gates and retains the
checkpoint. Stop the native workflow and children first: revocation cannot
cancel an in-flight command or undo already-applied edits.

## Reading and approving long plans

The reader keeps its header and controls visible; only the full plan body
scrolls. Use **↑/↓**, **Page Up/Page Down**, **Home/End**, or the mouse wheel in
fullscreen mode. Text wraps to the available width and reflows on resize.
**Enter** opens a separate compact confirmation stage; it does not approve.
The selection starts on **Cancel**. Use **Tab** or **←/→** to select
**Approve exact plan**, then **Enter**. **b** returns to the reader; **Esc**,
**Ctrl-C** or **q** cancels either stage without changing approval. Terminals
smaller than38 columns ×12 rows cannot approve until resized.

The complete document includes overall acceptance, assumptions, dependencies,
owned paths, task criteria, exact argv/timeouts, rollout and authorization limits.
Repository/model terminal-control characters are shown literally, not executed.
Each attempt also writes a private0600 `approval-review-<planHash>.json` containing
source identity and the full plan. RPC clients receive that file path and a
bounded **Cancel / Approve exact plan** selection, not unsupported custom TUI or
an oversized message. Opening a reader/artifact grants no authority. The
controller revalidates the original displayed plan/source under its lock after
confirmation; changes during either stage require a fresh review.

## Naming upgrade

The skill, package, executable and agent namespace are `badwater-senior-swarm`;
Pi settings use `badwaterSeniorSwarm` and Home Manager uses
`badwater.ai.pi.seniorSwarm`. Commands and resource names above have no retired-
name aliases. Rebuild through the consumer and restart Pi to unload the previous
package. Existing artifacts and worktrees are not deleted or relocated; the new
state/branch namespace starts separately. Inspect old evidence explicitly and
start a fresh review rather than copying a prior approval.

## Team and sequencing

The parent is coordinator/Scrum master. Only it delegates or changes the shared
board. Package roles are `badwater-senior-swarm.po`, `badwater-senior-swarm.tech-lead`, `badwater-senior-swarm.ux`, `badwater-senior-swarm.ui`,
`badwater-senior-swarm.developer`, `badwater-senior-swarm.qa`, `badwater-senior-swarm.security`, `badwater-senior-swarm.devops`.

1. Snapshot the repository, branch and clean/dirty source state.
2. PO/BPO and technical discovery establish users, requirements, invariants,
   scope/non-goals, acceptance assumptions and applicable specialists.
3. QA/security and only relevant UI/UX/DevOps review independently.
4. A fresh technical synthesis verifies/deduplicates findings and returns at
   most12 bounded tasks with owned paths, dependency DAG, criteria and checks.
   No justified work means an empty plan, not invented findings.
5. Stop for human approval. Approval covers isolated worktrees, exact proposed
   checks and local checkpoint commits on a dedicated integration branch only.
6. Dispatch disjoint ready developer tasks into native managed worktrees.
   Source must be clean; never auto-stash, reset or drop isolation.
7. Host gates reject no-change/out-of-scope/staged/symlink/submodule patches,
   run the approved checks and capture scoped patches. Serial integration
   commits only on the recorded `badwater-senior-swarm/<id>/integration` branch. Same-HEAD
   branch changes still block; nothing checks it back out automatically.
8. Run integrated checks and fresh HEAD-qualified QA/security, plus relevant
   UI/UX. Material findings may trigger at most two approved-scope repair cycles.
   Unknown scope, failures or budgets produce a retained checkpoint, not success.
9. Return the actual integration branch/head, result and evidence paths.
   No runtime push, main merge, activation, deployment or production operation.

Analysts use fresh context, project instructions and explicit read/search-only
tools, with no ambient extensions or nested delegation. Developers receive only
minimal writing/check tools and their exact assigned task. Tool filters and Git
worktrees are not an OS security boundary. Run untrusted code in an explicitly
approved sandbox/container, with only required data and credentials exposed.

## State, limits and evidence

Native mission state is the task-board index: source/plan identities, task owners
and statuses, dependency/acceptance contract pointers, evidence and blockers.
Detailed private artifacts live outside source under
`${XDG_STATE_HOME:-~/.local/state}/badwater-senior-swarm/<repository-hash>/<run-id>/`.
Directories are0700 and JSON is0600. Nothing reads auth.json, decrypts SOPS,
inspects recordings or starts browser/tunnel/services just to register resources.
Provider authentication during an explicitly requested model run remains Pi's
normal credential mechanism, not a new credential owner.

Defaults: six concurrent children,32 logical admissions across review/build,
two repairs. Review lanes are admitted durably before dispatch; continuation can
reuse their completed source/runtime-bound reports. Missing partial lanes retry
under the same logical claim. These limits are not a hard currency guarantee.
There is no new database, queue service, polling loop or nested review team.
Use native async completion/status/resume controls; inspect exact source and
partial work before a same-protocol retry, never switch agent CLIs silently.

The package uses registered named resources `badwater-senior-swarm.review/build`.
Raw workflow files are implementation references, not the supported launch
surface. Native host stdout has a4KiB preview limit: the controller returns
bounded control metadata and `planPath`, check/report and `resultPath` pointers.
Read full files before claims; a preview is not a complete report. Native debug
artifacts may expire; the private runDirectory is retained for explicit operator
cleanup. Never upload sessions/artifacts without separate consent.

Each finding separates severity from confidence and includes exact evidence,
trigger, impact, smallest remediation and regression criteria. Completed child
execution or prose alone is not proof. Command outcomes must distinguish pass,
findings, failure, unavailable and not attempted. A source-only UI observation
is not a visual or live accessibility result.

## Specialist capabilities

Curated pinned Superpowers, Impeccable, Trail of Bits and Vercel references retain
source provenance/licenses but do not activate upstream global bootstraps,
plugin agents, installers, detector downloads or nested workflows. Existing
Graphify/LSP/CDP and Ponytail remain available; a missing/stale graph falls back
to source, not automatic semantic extraction. Context7 uses the sole builtin MCP
owner, with operator OAuth and version/topic-only queries; do not send private
source. Missing OAuth/docs is a capability gap, not permission to add clients.

The Linux finite Playwright/axe helper requires a separately approved test URL
and data. It produces private desktop/narrow snapshots and partial accessibility
evidence through fresh isolated profiles, never a personal CDP session. The
coordinator owns it; screenshot sharing with a model needs consent and declared
model capability. Scanners are optional applicable evidence, with inspected
commands/rules/network use and fail-closed outcomes, not blanket security proof.

## Verified delivery and reproduction

Native x86_64 Linux acceptance covers:

-40 controller/workflow/branding/approval-UI tests;5 browser policy/lifecycle tests and one real
  isolated Chromium/axe synthetic smoke (no skipped smoke when enabled).
- Installed Pi1.4.0/subagents0.84 package/skill/eight-role discovery, zero resource
  warnings, exact host-peer identity, named script validation and lifecycle.
- Actual host prepare/collect with a plan larger than4KiB, headless/declined/raced
  approval, and the complete native build engine with explicitly emulated leaves
  but real scoped checks, Git worktrees, integration and final-review files.
- Before the full branding rename, a separately authorized live CLI/RPC pilot
  passed eight real role admissions, one actual confirmation, an isolated
  developer and Node test, serial integration, fresh QA/security on the exact
  final head and an unchanged caller source. That historical receipt does not
  certify the renamed package. The renamed interface is checked separately by
  the installed native SDK/workflow fixture above; no new model request is
  implied.

Development probes exposed and fixed missing fixture CA/shell/process tools,
planner-ID schema mismatch, native stdout preview truncation and undefined JSON
board state. A racy test-client filesystem watcher was replaced with native
`agent_settled` boundaries. Earlier failures are not relabeled passing receipts.
The explicit acceptance report is enabled for verified writer schemas; actual
host execution and fresh review still determine completion.

```sh
export NIX_CONFIG="${NIX_CONFIG-}"$'\nmax-jobs = 1\ncores = 3'
nix build .#badwater-senior-swarm .#checks.x86_64-linux.badwater-senior-swarm \
  .#checks.x86_64-linux.badwater-senior-swarm-native --no-link
nix build .#badwater-senior-swarm-browser --no-link
# Supply the exact installed helper; absence otherwise intentionally skips smoke.
BADWATER_SENIOR_SWARM_BROWSER_COMMAND=/nix/store/<built-browser>/bin/badwater-senior-swarm-browser \
  node --test pkgs/badwater-senior-swarm/tests/browser-smoke.test.mjs
nix flake check --no-build --all-systems
```

`tests/badwater-senior-swarm-live.mjs` is opt-in and quota-consuming, never automatic CI. It must
run under a private user/PID/mount namespace exposing only Nix store, synthetic
`/work`, a read-only auth input, managed `/bin/sh`, DNS and trusted CA roots.
Its working HOME must be `/work/home`; it copies auth only into that private
fixture for normal Pi authentication, never parses/prints it, and removes it.
The launcher must also remove the copy after namespace exit. Share network only
for the authorized provider calls; expose no real home/project/browser/socket.
The RPC client approves only the exact synthetic one-file/one-check plan and
uses native settled events, not polling. Do not run this script directly in a
real user home or against a real repository.

ARM Linux/Darwin were evaluated, not executed. No real Context7 OAuth request,
real product/browser/camera/media/service acceptance, system/kernel build,
activation or publication is implied by these checks. Private feature branches
remain behind the operator's manual sign-off before main/public adoption.
