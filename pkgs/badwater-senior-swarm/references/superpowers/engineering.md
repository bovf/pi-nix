# Engineering reference — adapted from Superpowers

Source: Jesse Vincent's [Superpowers](https://github.com/obra/superpowers/tree/2ce8aa15d05bd57213e6f746f953aafb7ded7a8b),
MIT; see LICENSE and ../sources.json. Modified: distilled for approval-bound,
parent-only orchestration. This is not the upstream workflow.

## Before implementation

Clarify the goal, acceptance criteria, source snapshot, interfaces, constraints
and non-goals. Read project rules and the actual named definitions/tests. A plan
must identify exact paths, concrete inputs/outputs, invariants and commands that
prove each task. Prefer small independently testable changes, reuse and the
simplest design needed now; do not invent future abstractions. Expose missing
product decisions before writing. The parent obtains human approval bound to the
plan and snapshot; an analysis child does not run commands or create a plan in
the checkout. Parent-owned mission storage replaces upstream repository-local
plan files and automatic execution handoffs.

## Test and implement

For each behavior change, specify a focused regression. When execution is
approved, observe the intended failure first, distinguish a real behavioral
failure from setup/import errors, implement the smallest correction, observe
success, then refactor while retaining coverage. Exercise the actual behavior,
not merely mock call counts. Keep existing green coverage. Configuration or
source-only work with no executable test must be labeled accordingly, not called
a passing regression. Do not delete unrelated work to imitate a test-first
sequence. Only the designated writer edits the approved isolated worktree.

## Debug from evidence

1. Read the complete error and reproduce with exact steps.
2. Inspect recent changes and trace inputs across component boundaries.
3. State one falsifiable root-cause hypothesis and a minimal approved experiment.
4. Verify the cause before changing code; avoid stacking speculative fixes.
5. When repeated fixes fail, stop and revisit assumptions with the parent.

Instrumentation must not expose secrets. A timeout or infrastructure failure is
not permission for another CLI/protocol path, nested delegation, or wider access.

## Verification before claims

Name the claim, identify the command that proves it, execute the complete
approved command on the exact integrated tree, read its full result/exit status,
and only then report the bounded claim with an artifact reference. Old runs,
source inspection, child self-report, partial commands and confidence are not
fresh proof. Separate tests actually run from tests proposed, non-native
evaluation from builds, and synthetic behavior from real-service acceptance.
After any integrated change invalidate prior independent QA/security evidence.
The parent enforces admission, repair budgets and explicit checkpoint authority;
this reference never authorizes commits, pushes, merges or deployment.
