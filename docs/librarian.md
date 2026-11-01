# Librarian: documentation is part of delivery

The Librarian checks documentation against source and keeps it useful to humans.
It is one specialist with two profiles: read-only
`badwater-senior-swarm.librarian` and approved
`badwater-senior-swarm.librarian-writer`.

## Review and plan

Every source review includes the Librarian alongside QA/security. It compares
README and linked docs with actual code, commands, options, defaults and tests.
Findings name the stale section, contradictory source, reader impact and smallest
correction. Missing evidence and optional readability suggestions stay distinct
from confirmed defects; clean documentation needs no manufactured edits.

The planner declares each task's `role`: `developer` (the default) or `librarian`.
Documentation tasks have explicit owned paths, acceptance criteria and checks.
New/changed features, interfaces and workflows need relevant documentation tasks,
or a source-grounded reason in assumptions explaining why no edit is needed.
Tasks that document code depend on those code tasks and read their integrated
implementation and handoffs—not merely the initial proposal. The approval viewer
shows the role and dependencies; they are included in the exact plan hash.

## Approved writing

Only an approved `role: librarian` task dispatches the writer, in its own managed
worktree at the current integration head. The host gate requires a real scoped
patch, permits `.md`, `.mdx`, `.rst` or `.adoc` changes plus explicitly scoped
bounded PNGs under documentation/image directories, and executes approved checks.
Screenshots need target/data/sharing/publication permission and source receipts;
the parent supplies captures, not ambient desktop tools. No application/configuration/dependency edits are authorized.
If no project doc checker exists, exactly `git diff --check` is a supported
tracked-diff whitespace check, not proof of new-file/link/content correctness.

Keep README a short entry point with essential usage and links. Put worthwhile
detail in focused `docs/` files; split mixed-purpose pages, remove duplication,
maintain useful links/anchors and preserve important warnings. Do not create
empty documentation trees, speculative manuals, invented commands, runtime
claims or repeated summaries. Repository-specific structure takes precedence.
See the [concise writing/review checklist](../pkgs/badwater-senior-swarm/references/documentation.md).

## Verify and repair

After integration, a fresh read-only Librarian checks the exact final HEAD
against source, approved changes, navigation and relevant new-feature guidance.
No passing writer summary substitutes for that review. Upstream repairs
invalidate dependent documentation tasks, so their writer runs again against
repaired code. Missing documentation outside approved paths requires a new plan
approval, not a hidden extra edit. Existing budgets and the two-cycle repair
limit still apply; the extra specialist counts toward logical admissions.

An explicit `roleModels."badwater-senior-swarm.librarian"` setting applies to both
profiles; absent overrides inherit the parent. Neither profile installs tools,
starts another team or grants production/credential/activation access. These
are source/workflow safeguards, not a guarantee that model output cannot be
wrong. [Workflow and human gate](badwater-senior-swarm.md).
