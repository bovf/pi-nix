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
packages.${system}.rpiv-todo
packages.${system}.pi-subagents
packages.${system}.plannotator-pi-extension
```

`pi-coding-agent` currently follows `nixpkgs-pi`; package extensions are built
Nix-natively from npm tarballs/lockfiles.

## Pi package registry

The overlay exposes a registry for declarative Home Manager config:

```nix
pkgs.piPackages.rpiv-todo
pkgs.piPackages.pi-subagents
pkgs.piPackages.plannotator-pi-extension
```

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
  rpiv-todo
  pi-subagents
  plannotator-pi-extension
];
```

## Apps / development

```bash
nix run .#fmt           # auto-format Nix files with Alejandra
nix run .#fmt -- --check
nix run .#update        # update flake + managed Pi/npm packages, then build
nix develop             # installs staged-file Alejandra pre-commit hook
```

`nix run .#update` maintains:

```text
pi-vim
rpiv-todo
pi-subagents
plannotator-pi-extension
```

and validates:

```text
pi-coding-agent
pi-vim
pi-search
pi-search-mcp
rpiv-todo
pi-subagents
plannotator-pi-extension
```
