# pi-nix

Standalone Nix flake for pi-coding-agent and related pi extensions.

## Outputs

```nix
overlays.default
overlays.pi-coding-agent
overlays.pi-vim
overlays.pi-search
packages.${system}.pi-coding-agent
packages.${system}.pi-vim
packages.${system}.pi-search
packages.${system}.pi-search-mcp
packages.${system}.rpiv-todo
packages.${system}.pi-subagents
```

The overlay also exposes a small registry for Home Manager modules:

```nix
pkgs.piPackages.rpiv-todo = {
  name = "rpiv-todo";
  package = pkgs.rpiv-todo;
};

pkgs.piPackages.pi-subagents = {
  name = "pi-subagents";
  package = pkgs.pi-subagents;
};
```

## Consumer example

```nix
inputs.pi-nix = {
  url = "path:/Users/dobrynikolov/Documents/Develop/Nix/repos/pi-nix";
  inputs.nixpkgs.follows = "nixpkgs";
};

# In nixpkgs overlays:
inputs.pi-nix.overlays.default
```
