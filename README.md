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
NIX_CONFIG="${NIX_CONFIG:+$NIX_CONFIG
}max-jobs = 2
cores = 4" nix run .#update  # update all pins/managed locks, then build
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

The updater refreshes Hunk's transitive flake inputs as well as nixpkgs/Hunk.
All ten managed npm locks are regenerated from package manifests, discarding
published lockfiles/shrinkwraps even when the top-level version is unchanged.
Upstream dependency constraints and existing dev/peer filtering are preserved;
for example, `@narumitw/pi-tui-kit` stays at `0.59.0` under `^0.59.0`, not the
incompatible `0.60.0` dist-tag. Pi core and Hunk retain their upstream build locks.

`pi-search` and `pi-search-mcp` remain local code and are build-validated against
the refreshed nixpkgs dependencies without an invented upstream version.

### Checked pins (2026-09-05)

| Package | Version |
| --- | --- |
| pi-coding-agent | 0.85.1 |
| pi-vim | 0.14.2 |
| hunk-review (Hunk) | 0.21.1 |
| rpiv-todo | 2.9.0 |
| pi-archimedes (and all 11 component packages) | 2.5.1 |
| pi-subagents | 0.65.1 |
| remote-pi | 0.7.0 (unchanged; nested lock refreshed) |
| plannotator-pi-extension | 0.27.12 |
| ponytail | 4.9.0 (unchanged) |
| pi-wait-what | 0.13.1 (unchanged) |
| pi-lsp | 0.49.6 |
| pi-chrome-devtools | 0.53.1 |
| pi-btw | 0.57.0 |
| pi-goal | 0.54.4 |

Regression checks: `python3 tests/update.py` (bash/jq required) exercises the
updater offline. `tests/load-extensions.mjs` uses Pi's resource loader; run with
Node from an empty HOME/cwd under `unshare -Urn` on Linux, passing the Pi store
path then extension package store paths. This checks factories/resources only,
not model calls, session lifecycle, browsers, LSP servers or remote services.

All outputs below were built on `x86_64-linux`; `pi --version` returned `0.85.1`.
Every packaged extension/Hunk resource loaded individually and together in an
empty HOME/cwd with networking disabled. Local search usage and the MCP
initialize/list-tools/empty-query path passed offline. All package derivations
also evaluated on `aarch64-linux` and `aarch64-darwin` (not cross-built).

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
