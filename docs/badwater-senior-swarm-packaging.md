# Badwater Senior Swarm packaging, references and browser evidence

This producer exports `pkgs.badwater-senior-swarm`,
`pkgs.piPackages.badwater-senior-swarm = { name = "badwater-senior-swarm"; package = pkgs.badwater-senior-swarm; }`,
`packages.<system>.badwater-senior-swarm` and `overlays.badwater-senior-swarm` (also composed
into `overlays.default`). The package root is the copied `pkgs/badwater-senior-swarm`
runtime: manifest, extension, library, CLI, `approval-ui.mjs`, workflows, roles, skill, references
and tests. `bin/badwater-senior-swarm` invokes the installed CLI with managed Node.
There is no npm install, runtime downloader, global bootstrap or configuration
mutation at package installation time.

Host policy and activation belong to `badwater-ai`; Heavy/Spy choices belong to
`pl-badwater`. This output alone does not enable a swarm, select a model, install
an MCP entry, authorize commands, approve a build or activate a generation.
Use the extension's named `badwater-senior-swarm.review` and `badwater-senior-swarm.build`
resources through Pi/subagents, not raw workflow-file launches that could bypass
the approval/state gates. Build approval requires the interactive
`/badwater-senior-swarm-approve` flow bound to the plan/source; headless approval fails closed.
The host Pi TUI peer supplies Text/ScrollView for a bounded two-stage reader;
no second renderer, pager dependency or browser UI is added. RPC uses a private
complete review artifact plus a compact Cancel-first selection.

## Exact host dependencies and paths

The package links the actual selected host modules from
`${pi-coding-agent}/lib/pi/node_modules` for
`@earendil-works/{pi-coding-agent,pi-ai,pi-agent-core,pi-tui}` and `typebox`.
`node_modules/pi-subagents` links the selected `pkgs.pi-subagents` root. There
are no npm copies of these peers. Runtime imports must use the official exported
Pi/subagents interfaces; package paths do not confer access to internal APIs.

Generated `paths.json` is a flat object (all non-null paths absolute):

```json
{
  "node": "/nix/store/<host-node>/bin/node",
  "git": "/nix/store/<git>/bin/git",
  "shell": "/nix/store/<bash>/bin/bash",
  "runtimePath": "/nix/store/<procps>/bin",
  "browser": "/nix/store/<browser-package>/bin/badwater-senior-swarm-browser",
  "pi": "/nix/store/<pi>/lib/pi/node_modules/@earendil-works/pi-coding-agent",
  "subagents": "/nix/store/<pi-subagents>"
}
```

`browser` is null on unsupported platforms. Browser is a separate derivation;
it never depends on the swarm runtime package, avoiding a dependency cycle.
Nix store paths retain string context in generated JSON. The extension adds the
managed `runtimePath` to this Pi process's PATH (deduplicated); native host-step
cleanup requires `ps`, including in minimal shells. It changes no shell files or
persistent settings. Native host commands also require the platform's `/bin/sh`.

Runtime settings are `badwaterSeniorSwarm` in Pi's
`~/.pi/agent/settings.json` (Home Manager producer:
`extraSettings.badwaterSeniorSwarm`). Precedence is runtime defaults, then generated
browser path fallback, then explicit settings. Explicit `browserCommand: null`
disables the helper rather than restoring a fallback. Defaults are
`maxConcurrent: 6`, `maxAgents: 32`, `maxRepairCycles: 2`, `roleModels: {}`.
Missing role overrides inherit the parent model/provider; a `roleModels` entry
may use the bare role or `badwater-senior-swarm.role`. No package changes provider/model defaults.
`badwater-ai` owns option validation, platform assertions and Context7/MCP merging;
its browser disable policy must emit the explicit null override. Package presence
is not permission to use the browser or a model.

## Curated references and licenses

[`references/README.md`](../pkgs/badwater-senior-swarm/references/README.md) is the
reference index; `sources.json` records immutable upstream commits, source URLs
and SHA256 for each original document used. Shipped guides are deliberately
distilled instead of activating upstream delegation, shell/write privileges,
installer, CDP attachment, live fetching or deployment instructions:

| Guide | Source and license |
|---|---|
| `superpowers/engineering.md` | obra/superpowers, Jesse Vincent, MIT |
| `impeccable/ui-ux.md` | pbakaus/impeccable, Paul Bakaus, Apache-2.0 |
| `trail-of-bits/security.md` | trailofbits/skills contributors, CC-BY-SA-4.0 |
| `vercel-react/react.md` + five verbatim rule examples | vercel-labs/agent-skills, Vercel Engineering, declared MIT |
| `vercel-web/web.md` | vercel-labs/web-interface-guidelines, Vercel Labs, MIT |

Original license/notice files are retained. Vercel React has no standalone
LICENSE upstream; its original MIT-declaring skill is retained as attribution,
not activated. Trail of Bits adaptation explicitly remains CC-BY-SA-4.0; this
separate reference document does not relicense the independent runtime or other
works. No upstream detector/scanner is bundled or represented as having run.
Updates require reviewed source/provenance/license changes, never a latest-source
fetch at runtime.

## Browser interface and isolation

`pkgs.badwater-senior-swarm-browser` / `packages.<linux-system>.badwater-senior-swarm-browser`
provides one finite command:

```sh
badwater-senior-swarm-browser --url http://127.0.0.1:8080/example \
  --output /absolute/path/to/new-private-evidence-directory
# Each additional exact origin needs separate explicit task authorization:
badwater-senior-swarm-browser --url https://preview.example.invalid/page \
  --allow-origin https://preview.example.invalid \
  --output /absolute/path/to/another-new-evidence-directory
```

The command prints JSON `{ "report": "/absolute/.../report.json" }` only on
success; failure exits nonzero. It never starts a development server. The output
directory must not exist and is created mode0700; it must be outside source and
contain no pre-existing data. Do not supply credentials/tokens in URLs or args.
This is **not** a general browser automation/CDP endpoint, shell command runner,
installer, authenticated profile reader or indefinite service.

- Pinned nixpkgs `playwright-driver` **1.64.1** with its matching Chromium and
  headless-shell browser revisions; no independent browser download.
- `axe-core` **4.10.3** immutable npm tarball, SHA512
  `Xm7bpRXnDSX2YE2YFfBk2FnF0ep6tmG7xPh8iHee8MIcrgq762Nkce856dYtJYLkuIoYZvGfTs/PbZhideTcEg==`.
  Only its JS, README and MPL-2.0 license are extracted; no lifecycle scripts.
- Each command launches a fresh sandboxed Chromium, two fresh contexts, no host
  CDP, profile, cookies, storage, credentials, display or existing tabs.
- Bubblewrap supplies a private user/PID/mount/network namespace, read-only Nix
  store, synthetic HOME/temp, proc/dev and only the new evidence directory.
  The browser has no host network. No caller working tree or home is mounted.
- Parent Node mediates HTTP over bounded stdio. Only GET/HEAD to exact authorized
  HTTP(S) origins are permitted, without host credentials/headers. Numeric
  `127.0.0.1`/`[::1]` target origins are default-authorized; other targets
  (including DNS `localhost`) need `--allow-origin`. No wildcard, path,
  query/fragment or userinfo is accepted in extra-origin authorization.
- Cross-origin redirects must pass the same policy at every hop. All WebSockets,
  service workers, direct external browser networking, file navigation access,
  and attachment/download publication are blocked. An authorized target may
  still process GET requests; explicit approval must account for that risk.
- Whole invocation deadline60s; request timeout10s, navigation15s; max128 HTTP
  requests, 8MiB per response, 4MiB per JSON evidence file, fixed viewport PNGs.
  Oversized/unavailable inputs fail or become blocked requests, never a success
  claim for omitted checks. Namespace/launch failure stops; no unsandboxed,
  alternative CLI/protocol or host-browser fallback exists.

Evidence files: `desktop.png` (1440x900), `mobile.png` (390x844, mobile/touch
**emulation**), `desktop.axe.json`, `mobile.axe.json`, `report.json` with browser
version, axe version, viewports, filenames, violation/incomplete counts and
blocked request/WebSocket/download counters. Axe includes violation/incomplete
rule/node evidence, not a blanket pass verdict. These snapshots do not test
all states, keyboard/touch journeys, physical devices, performance, native apps
or complete WCAG compliance. Human visual review is separate from axe results.
A failed capture may leave partial private artifacts; absence of a complete
report is not passing evidence. No automatic cleanup of caller artifacts occurs.

## Validation and platform scope

Main package/Node runtime checks advertise x86_64-linux, aarch64-linux and
aarch64-darwin. Browser advertises only x86_64-linux/aarch64-linux; it requires
Linux user namespaces/Bubblewrap and Chromium sandbox support. Darwin browser
is not exported, substituted or cross-built. Non-native evaluation is not a
claim of execution.

```sh
export NIX_CONFIG="${NIX_CONFIG-}"$'\nmax-jobs = 1\ncores = 3'
nix build .#badwater-senior-swarm .#checks.x86_64-linux.badwater-senior-swarm \
  .#checks.x86_64-linux.badwater-senior-swarm-native --no-link
nix build .#badwater-senior-swarm-browser --no-link
BADWATER_SENIOR_SWARM_BROWSER_COMMAND=/nix/store/<built-browser>/bin/badwater-senior-swarm-browser \
  node --test pkgs/badwater-senior-swarm/tests/browser-smoke.test.mjs
node --test pkgs/badwater-senior-swarm/tests/browser-policy.test.mjs \
  pkgs/badwater-senior-swarm/tests/browser-lifecycle.test.mjs
nix flake check --no-build --all-systems
```

The runtime check runs actual `node --test` on `tests/*.test.mjs` excluding
`browser*.test.mjs`, in private HOME/temp with managed Git/Node and `PI_OFFLINE=1`.
It fails if no runtime tests exist. Browser's mandatory Nix install check runs
policy units; actual Chromium smoke is a separate private synthetic test because
nested user namespaces are not assumed in Nix builders. Smoke requires the
explicit installed command environment variable (otherwise reports skipped),
starts only synthetic loopback fixtures, verifies two PNGs and real axe
`button-name` findings, and proves disallowed origin/redirect/POST traffic never
reaches a second synthetic listener. It checks WebSocket/download blocking too.
No real service, model call, cookies, production page or login is used.
The native check loads the actual installed SDK/package roles/skill, requires
zero resource warnings, validates both named resources, exercises real host
prepare/large-plan collect calls, approval refusal/race and shutdown, and runs
the entire build script through the native workflow engine with explicitly
emulated leaves and real Git/check/gate/integration operations. This offline
fixture is not a live-model claim. The separate quota-consuming CLI/RPC pilot
and its boundaries are documented in [seniorSwarm.md](badwater-senior-swarm.md); it is never automatic
CI. Browser-only evidence does not certify orchestration or policy.
