# pi-nix

Nix flake for `pi-coding-agent` and maintained Pi extensions/packages.

This repo is package/build logic only. Home Manager policy lives in
[`badwater-ai`](git@gitlab.dobryops.com:nix/badwater-ai.git); host choices live
in `pl-badwater`.

## Remote

```text
git@gitlab.dobryops.com:nix/pi-nix.git
```

## Outputs

```nix
overlays.default
overlays.pi-coding-agent
overlays.pi-vim
overlays.pi-search
overlays.pi-packages

packages.${system}.pi-coding-agent
packages.${system}.pi-vim
packages.${system}.pi-search
packages.${system}.pi-search-mcp
packages.${system}.hunk-review
packages.${system}.rpiv-todo
packages.${system}.pi-archimedes
packages.${system}.pi-subagents
packages.${system}.remote-pi
packages.${system}.plannotator-pi-extension
packages.${system}.ponytail
packages.${system}.pi-wait-what
packages.${system}.pi-lsp
packages.${system}.pi-chrome-devtools
packages.${system}.pi-btw
packages.${system}.pi-goal
```

`pi-coding-agent` tracks npm's `latest` version, built from the matching
`earendil-works/pi` Git tag and its upstream workspace lockfile. Git tags omit
generated model data, so the matching, integrity-pinned `@earendil-works/pi-ai`
npm catalog is copied in and validated by upstream's offline build. This also
covers npm releases published before GitHub release assets are available.
The upstream `build:offline` script builds the matching workspaces with TypeScript
7, including the new codemode, MCP, durable and SQLite session backend packages.
These and `pi-server` (including `pi-server/unix`) are installed alongside the
other host peers. `pi-subagents` 0.73 uses native SDK sessions inside its detached
runner, not the older Unix-server transport or an extension-local Pi fallback;
all required peers must resolve to host Pi 0.99.1.
Extensions are built Nix-natively from npm tarballs, managed lockfiles, or pinned
GitHub sources; no runtime/global npm installation is needed.

## Pi package registry

The overlay exposes a registry for declarative Home Manager config:

```nix
pkgs.piPackages.hunk-review
pkgs.piPackages.rpiv-todo
pkgs.piPackages.pi-archimedes
pkgs.piPackages.pi-subagents
pkgs.piPackages.remote-pi
pkgs.piPackages.plannotator-pi-extension
pkgs.piPackages.ponytail
pkgs.piPackages.pi-wait-what
pkgs.piPackages.pi-lsp
pkgs.piPackages.pi-chrome-devtools
pkgs.piPackages.pi-btw
pkgs.piPackages.pi-goal
```

`hunk-review` reuses the skill shipped in Hunk's own flake package; it does not copy or fork the upstream skill. The packaged `pi-archimedes` leaves clipboard images to Pi core and delegation to `pi-subagents`, avoiding duplicate shortcuts and tools.

Each entry is shaped like:

```nix
{
  name = "pi-subagents";
  package = pkgs.pi-subagents;
}
```

## Consumer example

```nix
inputs.pi-nix = {
  url = "git+ssh://git@gitlab.dobryops.com/nix/pi-nix.git";
  inputs.nixpkgs.follows = "nixpkgs";
};

# In nixpkgs overlays:
inputs.pi-nix.overlays.default
```

Then in a `badwater-ai` consumer:

```nix
badwater.ai.pi.packages = with pkgs.piPackages; [
  hunk-review
  pi-archimedes
  pi-subagents
  remote-pi
  plannotator-pi-extension
  ponytail
  pi-wait-what
  pi-lsp
  pi-chrome-devtools
  pi-btw
  pi-goal
];
```

## Apps / development

```bash
nix run .#fmt           # auto-format Nix files with Alejandra
nix run .#fmt -- --check
# Preserve existing Nix configuration while limiting this update's builds:
export NIX_CONFIG="${NIX_CONFIG-}"$'\nmax-jobs = 2\ncores = 4'
nix run .#update        # update all pins/managed locks, then build
nix develop             # installs staged-file Alejandra pre-commit hook
```

`nix run .#update` maintains every upstream pin (and refreshes the nixpkgs/Hunk flake inputs):

```text
pi-coding-agent
pi-vim
hunk-review (Hunk flake input)
rpiv-todo
pi-archimedes
pi-subagents
remote-pi
plannotator-pi-extension
ponytail
pi-wait-what
pi-lsp
pi-chrome-devtools
pi-btw
pi-goal
```

The updater refreshes Hunk's transitive flake inputs as well as nixpkgs/Hunk:
`hunk/bun2nix`, `hunk/systems`, `hunk/bun2nix/flake-parts`, and
`hunk/bun2nix/treefmt-nix`. The final graph has no additional unfollowed paths.
If GitHub's anonymous release API is rate-limited, Ponytail's latest stable tag
is resolved through the public latest-release redirect instead.
All ten managed npm locks are regenerated from package manifests, discarding
published lockfiles/shrinkwraps even when the top-level version is unchanged.
Upstream dependency constraints and existing dev/peer filtering are preserved:
`pi-chrome-devtools` and `pi-goal` retain `@narumitw/pi-tui-kit` `0.59.0` under
`^0.59.0`; `pi-btw` retains `0.64.0` under `^0.64.0`, not the incompatible
`0.65.1` dist-tag. Pi core and Hunk retain their matching upstream build locks.
Update builds retain GC roots in a printed temporary directory outside the repo;
remove that directory when the outputs are no longer needed.

`pi-search` and `pi-search-mcp` remain local code and are build-validated against
the refreshed nixpkgs dependencies without an invented upstream version.

### Checked pins (2026-09-30)

| Package | Version |
| --- | --- |
| pi-coding-agent | 0.99.1 |
| pi-vim | 0.14.2 (unchanged) |
| hunk-review (Hunk) | 0.22.0 (unchanged version; upstream HEAD refreshed) |
| rpiv-todo | 2.11.0 |
| pi-archimedes (and all 11 component packages) | 2.8.0 |
| pi-subagents | 0.73.1 |
| remote-pi | 0.7.0 (unchanged; nested lock refreshed) |
| plannotator-pi-extension | 0.27.22 |
| ponytail | 4.10.0 (unchanged) |
| pi-wait-what | 0.13.1 (unchanged; regenerated lock identical) |
| pi-lsp | 0.49.8 (unchanged; regenerated lock identical) |
| pi-chrome-devtools | 0.53.4 (unchanged; regenerated lock identical) |
| pi-btw | 0.61.1 |
| pi-goal | 0.54.8 (unchanged; regenerated lock identical) |

Regression checks: `python3 tests/update.py` (bash/jq required) exercises the
updater offline. `tests/load-extensions.mjs` uses Pi's resource loader; run with
Node from an empty HOME/cwd under `unshare -Urn` on Linux, passing the Pi store
path then extension package store paths. This checks factories/resources only,
not model calls, session lifecycle, browsers, LSP servers or remote services.
The standalone Node loader reports pi-subagents' host-detection warning and
keeps its tool eagerly available; it does not verify dynamic-tool host behavior.
Extension warnings are emitted separately from errors and resource diagnostics.
Pi warns that remote-pi declares Pi core/TUI and typebox as dependencies, and
rpiv-todo declares typebox likewise, rather than wildcard host peers. Their local
copies are retained under upstream constraints: remote-pi has Pi 0.79.10, and both
have typebox 1.3.34 (host: Pi 0.99.1/typebox 1.3.27). No active host-alias bypass was
demonstrated; plain native resolution to these copies is not proof of one.
These checks use the unbundled SDK, not the CLI bundle's embedded-module loader.
CLI version/help checks do not establish bundled extension-loading coverage.

`tests/subagents-host-peers.mjs` additionally runs the installed pi-subagents
host-peer resolver and checks every required alias (13 in this release, including
Chord), plus the four newly packaged workspaces, against the matching Pi output.
It launches the installed `subagent-runner-bootstrap.js` with its native
`runner-peer-preload.mjs`, `JITI_ALIAS`, host package roots and
`PI_ASYNC_NATIVE_RUNNER=1`. Version 0.73 reads config before importing its heavy
runner: a missing-config probe alone no longer proves peer loading. Instead,
an inert config points `asyncDir` at a regular fixture file, reaching the default
heavy-module import and failing at initial storage setup before task dispatch.
An absent-alias negative control fails earlier at a host-peer import. A child process using the same preload/environment
verifies all bare peer imports resolve to the host, calls the default background
SDK session factory without a loader override, verifies startup/shutdown hooks,
and disposes an in-memory session without prompting or calling a model.
Separately, it checks the retained Pi server/client/protocol APIs with upstream's
in-memory test host and a Unix handshake. That handshake is not pi-subagents'
current transport.
This does not exercise the detached runner's full scheduling/steering/task loop
or remote placement. Run with Node 24 from an empty HOME/cwd, for example:

```bash
export NIX_CONFIG="${NIX_CONFIG-}"$'\nmax-jobs = 2\ncores = 4'
roots=$(mktemp -d)
core=$(nix build .#pi-coding-agent --out-link "$roots/core" --print-out-paths)
subagents=$(nix build .#pi-subagents --out-link "$roots/subagents" --print-out-paths)
test="$PWD/tests/subagents-host-peers.mjs"
node=$(command -v node)
home=$(mktemp -d)
(cd "$home" && env -i HOME="$home" PATH="$PATH" PI_OFFLINE=1 \
  timeout 60 unshare -Urn "$node" "$test" "$core" "$subagents")
rm -rf "$home"
```

All outputs below were built on `x86_64-linux`; `pi --version` returned `0.99.1`.
Every packaged extension/Hunk resource loaded individually and together in an
empty HOME/cwd with networking disabled (12 extension factories, 11 skills and
6 prompt templates; no resource diagnostics). Local search usage and the MCP
initialize/list-tools/empty-query path passed offline. Its nixpkgs-supplied ddgr
2.2, Python 3.14.7 and MCP 1.29.0 versions are unchanged, with refreshed derivations.
All package derivations also evaluated on `aarch64-linux` and `aarch64-darwin`
(not cross-built). Hunk upstream HEAD `0a67560cfd4f4ad2a01251018c4caa538a1f107a`
uses `stdenv.hostPlatform.isLinux` in `nix/package.nix:38`, fixing the historical
`stdenv.isLinux` warning upstream; no consumer suppression is applied.

Downstream consumers must refresh their followed nixpkgs and Hunk inputs plus
the four transitive Hunk paths above, not just the pi-nix revision. Preserve
`badwater-ai`'s package symlinks and Archimedes image-paste/subagent exclusions;
revalidate generated MCP configuration and the selected MCP implementation
separately from factory loading. Private update branches are not mirrored: the mirror pipeline
only publishes default-branch pushes. Local builds do not establish published
GitLab integration or deployed-state compatibility.

Validated outputs:

```text
pi-coding-agent
pi-vim
pi-search
pi-search-mcp
hunk-review
rpiv-todo
pi-archimedes
pi-subagents
remote-pi
plannotator-pi-extension
ponytail
pi-wait-what
pi-lsp
pi-chrome-devtools
pi-btw
pi-goal
```
