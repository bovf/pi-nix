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
other host peers. `pi-subagents` 0.74 uses native SDK sessions inside its detached
runner, not the older Unix-server transport or an extension-local Pi fallback;
all required peers must resolve to host Pi 0.99.2.
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

### Checked pins (2026-10-01)

| Package | Previous → current |
| --- | --- |
| pi-coding-agent | 0.99.1 → 0.99.2 |
| pi-vim | 0.14.2 (unchanged) |
| hunk-review (Hunk) | 0.22.0 → 0.23.0 |
| rpiv-todo | 2.11.0 → 2.12.0 |
| pi-archimedes | 2.8.0 → 2.9.0 (12 exact component pins audited) |
| pi-subagents | 0.73.1 → 0.74.0 |
| remote-pi | 0.7.0 (unchanged; host-peer packaging repaired) |
| plannotator-pi-extension | 0.27.22 → 0.27.24 |
| ponytail | 4.10.0 (unchanged) |
| pi-wait-what | 0.13.1 (unchanged) |
| pi-lsp | 0.49.8 (unchanged) |
| pi-chrome-devtools | 0.53.4 (unchanged) |
| pi-btw | 0.61.1 (unchanged) |
| pi-goal | 0.54.8 (unchanged) |

All ten managed locks were regenerated; the five `@narumitw` locks are identical.
All six final flake pins were checked against their declared upstream refs.
Only Hunk moved, to `aa23ba29ae233a480b1b3c2c20c1c25018246ee6`; nixpkgs and the
four transitive Hunk pins are unchanged. Hunk still uses
`stdenv.hostPlatform.isLinux`, without consumer warning suppression.
Pi's npm latest and GitHub latest release both report 0.99.2; the build uses the
matching tag/workspace lock and integrity-pinned npm model catalog, not a
substitute release asset.

### Host peers and regression checks

`remote-pi` 0.7.0 still declares Pi core/TUI and typebox as private dependencies
upstream. `pkgs/remote-pi/host-peers.jq` normalizes only these three packages to
wildcard peers, shared by the updater and build. Its managed lock contains no
private host copies. The output links the exact host modules for its native ESM
and standalone CLI consumers, which cannot rely on Pi's extension aliases.
`rpiv-todo` 2.12.0 fixes its typebox peer upstream; no local patch is needed.
Other package constraints remain unchanged.

- `python3 tests/update.py` (bash/jq required) checks the updater offline,
  including shared peer normalization and the copy-free remote-pi lock.
- `tests/remote-pi-host-peers.mjs` checks native ESM realpath/module identity,
  both standalone CLI import/help paths, and negative controls for the old
  manifest warning and a manifest-only repair retaining conflicting copies.
  Use Node's `--experimental-import-meta-resolve` flag for this test's explicit
  parent-URL resolution; CJS `require.resolve` does not support these ESM-only
  exports.
- `tests/load-extensions.mjs` checks every packaged factory/resource and rejects
  all host-peer warnings. All 13 selections and their combined load passed
  (12 factories, 10 skills, 6 templates), with empty stderr. Subagents 0.74 also
  fixes the previous standalone-SDK host-detection warning upstream.
- `tests/subagents-host-peers.mjs` exercises the installed native preload,
  `JITI_ALIAS`, real `subagent-runner-bootstrap.js` heavy import, and absent-alias
  negative control. Its uninjected background SDK factory creates/disposes an
  in-memory session with startup/shutdown hooks, without prompting. All 13
  current aliases resolve to Pi 0.99.2. The matching server/client `/unix`
  handshake is tested separately, not misidentified as subagents' transport.
- `tests/bundled-cli.mjs` runs the actual installed `bin/pi` (the bundled Node
  entrypoint), loads packaged extensions, checks RPC startup/EOF shutdown and
  resource commands, and rejects stderr/warnings/errors. It never sends a
  prompt. Archimedes 2.9 removed its MCP component upstream; the inert fixture
  retains `archimedes.mcp.enabled=false` and checks exactly one builtin `/mcp`.
  Clipboard-image/delegation exclusions remain intact. For an already generated
  isolated Home Manager fixture, pass `<core> --existing-settings` instead of
  package paths. This retains its package selection, extensions and preferences,
  appends only the inert probe, rejects settings mutation and restores the original
  settings bytes. Never point it at a live home.

Run runtime checks only in an empty, private filesystem **and** network
namespace. An empty HOME or `unshare -Urn` alone does not isolate absolute home
paths and host Unix sockets. Inspect startup hooks and installed wrappers when
upgrading; never reuse live settings/auth. For example, on Linux:

```bash
export NIX_CONFIG="${NIX_CONFIG-}"$'\nmax-jobs = 2\ncores = 4'
roots=$(mktemp -d)
nix build .#pi-coding-agent --out-link "$roots/core"
nix build .#remote-pi --out-link "$roots/remote"
nix build .#rpiv-todo --out-link "$roots/todo"
nix build --inputs-from . nixpkgs#nodejs --out-link "$roots/node"
nix build --inputs-from . nixpkgs#bubblewrap --out-link "$roots/bwrap"
node="$(readlink -f "$roots/node")/bin/node"
core=$(readlink -f "$roots/core")
remote=$(readlink -f "$roots/remote")
todo=$(readlink -f "$roots/todo")
fixture=$(mktemp -d)
"$roots/bwrap/bin/bwrap" --unshare-all --die-with-parent --new-session \
  --ro-bind /nix/store /nix/store --proc /proc --dev /dev --tmpfs /tmp \
  --bind "$fixture" /fixture --ro-bind "$PWD/tests" /tests --chdir /fixture \
  --clearenv --setenv HOME /fixture --setenv PATH "$(dirname "$node")" \
  --setenv PI_OFFLINE 1 "$node" --experimental-import-meta-resolve \
  /tests/remote-pi-host-peers.mjs "$core" "$remote" "$todo"
rm -rf "$fixture"
```

Use a fresh fixture with the same sandbox for `load-extensions.mjs` or
`bundled-cli.mjs`, passing the core then the desired package store paths;
`subagents-host-peers.mjs` takes core and subagents. Only the native peer test
needs the experimental resolver flag. Keep build roots until validation ends.

All 16 native outputs were realized on `x86_64-linux`. Local search usage and
MCP initialize/list-tools/empty-query checks passed without a web query; their
nixpkgs dependencies remain ddgr 2.2, Python 3.14.7 and MCP 1.29.0.
All derivations also evaluated on `aarch64-linux` and `aarch64-darwin`, without
cross-build claims. `nix flake check --no-build --all-systems` evaluates the
flake; it is not an additional realization (and retains the existing six app
`meta` warnings). Independent redacted Gitleaks and offline TruffleHog passed.
These gates do not cover full TUI workflows, model/provider calls, browser/LSP
services, remote placement, daemon fleet operations or hardware.

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
