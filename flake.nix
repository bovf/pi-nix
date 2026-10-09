{
  description = "Nix flake for pi-coding-agent and related pi extensions";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";

    pi-upstream = {
      url = "github:earendil-works/pi/stable";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    hunk = {
      url = "github:modem-dev/hunk";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = {
    self,
    nixpkgs,
    hunk,
    pi-upstream,
    ...
  }: let
    systems = [
      "x86_64-linux"
      "aarch64-linux"
      "aarch64-darwin"
    ];

    forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f system);

    appsLib = import ./nix/apps {inherit nixpkgs;};
    shellsLib = import ./nix/shells;

    piVimOverlay = import ./overlays/pi-vim {};
    piSearchOverlay = import ./overlays/pi-search {};
    piPackagesOverlay = import ./overlays/pi-packages {inherit hunk;};
    piCodingAgentOverlay = import ./overlays/pi-coding-agent {inherit pi-upstream;};

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
      inherit (pkgs) pi-vim pi-search pi-search-mcp rpiv-todo pi-archimedes pi-subagents remote-pi plannotator-pi-extension ponytail pi-wait-what pi-lsp pi-chrome-devtools pi-btw pi-goal pi-coding-agent;
      hunk-review = pkgs.piPackages.hunk-review.package;
      default = pkgs.pi-coding-agent;
    });

    # This package runs the footer checks during its build, not only via flake check.
    checks = forAllSystems (system: {
      archimedes-footer = self.packages.${system}.pi-archimedes;
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
