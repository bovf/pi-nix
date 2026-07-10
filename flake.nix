{
  description = "Nix flake for pi-coding-agent and related pi extensions";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

    hunk = {
      url = "github:modem-dev/hunk";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = {
    self,
    nixpkgs,
    hunk,
    ...
  }: let
    systems = [
      "x86_64-linux"
      "aarch64-linux"
      "x86_64-darwin"
      "aarch64-darwin"
    ];

    forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f system);

    appsLib = import ./nix/apps {inherit nixpkgs;};
    shellsLib = import ./nix/shells;

    piVimOverlay = import ./overlays/pi-vim {};
    piSearchOverlay = import ./overlays/pi-search {};
    piPackagesOverlay = import ./overlays/pi-packages {inherit hunk;};
    piCodingAgentOverlay = import ./overlays/pi-coding-agent {};

    defaultOverlay = final: prev:
      (piVimOverlay final prev)
      // (piSearchOverlay final prev)
      // (piPackagesOverlay final prev)
      // (piCodingAgentOverlay final prev);
  in {
    overlays = {
      default = defaultOverlay;
      pi-vim = piVimOverlay;
      pi-search = piSearchOverlay;
      pi-packages = piPackagesOverlay;
      pi-coding-agent = piCodingAgentOverlay;
    };

    packages = forAllSystems (system: let
      pkgs = import nixpkgs {
        inherit system;
        overlays = [self.overlays.default];
        config.allowUnfree = true;
      };
    in {
      inherit (pkgs) pi-vim pi-search pi-search-mcp rpiv-todo pi-archimedes pi-subagents plannotator-pi-extension ponytail pi-wait-what pi-lsp pi-chrome-devtools pi-btw pi-goal pi-coding-agent;
      default = pkgs.pi-coding-agent;
    });

    apps = forAllSystems (system: appsLib.mkApps system);

    devShells = forAllSystems (system: let
      pkgs = nixpkgs.legacyPackages.${system};
      apps = appsLib.mkApps system;
    in
      shellsLib {
        inherit pkgs;
        fmtApp = apps.fmt;
      });
  };
}
