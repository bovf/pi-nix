# Craft runtime compatibility — 2026-11-05

Originally tested on `chore/update-craft-stack-2026-11-05`, now promoted with the
operator's approval to canonical `main` and its source-only GitHub/Codeberg mirrors.
This keeps Pi 1.5.0, all parent/npm pins, model/context preferences and existing
runtime permissions. Public consumers use `github:bovf/pi-nix`; no activation
or permission to resume old workflows accompanies source publication.

Updated LightCraft 0.18.1 extends its normal library-load report with `repaired: []`.
The private Craft MCP launcher previously rejected that new field as an unknown
diagnostic, correctly blocking the consumer video/native catalog gate. Its
narrow healthy-report recognizer now accepts the old shape or the new **empty**
repair list, once only, for the exact private library path. Non-empty repairs,
damage, stale/failed/torn data, upgrades, warnings, unknown fields and mismatched
paths remain diagnostics and are not suppressed. Accepted informational lines
remain retained in the private `startup.log`.

VectorCraft 0.21.1 rewords its exact confinement announcement to `read /; write
<private-root>`. The launcher retains that source-proven informational line once,
for the exact namespace write root; other text stays diagnostic.

PhotoCraft 0.20.2's memory detector correctly refuses PSD/TIFF opens when a
namespace hides its cgroup constraints. Only that native companion now mounts a
private read-only cgroup v2 view during namespace setup, then drops all child
capabilities and sets no-new-privileges before the editor starts. It does not bind
the host cgroup tree, weaken memory limits, broaden media/workspace roots or add
network access. Other eleven backends keep their original namespace construction.
Linux requires these unprivileged namespace/kernel facilities; failure stays
closed, without a less-confined fallback or daemon configuration change.

The current Python MCP SDK distinguishes anticipated `ToolError` refusals from
unexpected crashes. The video's stdio boundary now maps only its engine's
`ValueError` validation failures to the public `ToolError`, retaining all 38
names/descriptions/input/output signatures and strict boolean consent. CLI
validation is unchanged. Runtime/invariant failures remain unexpected errors;
they are not swallowed or converted to success. Installed SDK tests exercise
both classes and rejected string/numeric/null consent; the real editorial stdio
gate separately checks refused final exports without an unexpected traceback.

The package install check runs old/new healthy and unhealthy-report regressions,
actual private filesystem/cgroup/capability checks and a mount-failure negative. The actual updated-application native catalog/batch and synthetic
video/editorial tests are separate acceptance gates; historical receipts are not
relabeled. No new applications are added to the launcher's twelve verified
private-namespace backends merely because their GUI/CLI is installed. Craft
Anything has its own disabled/read-first integration in the policy owner.

The known swarm pre-integration patch-recapture lifecycle defect remains outside
this update. Old failed runs/approvals/worktrees are untouched and do not migrate
authority to a changed runtime.
