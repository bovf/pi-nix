{
  description = "Nix flake for pi-coding-agent and related pi extensions";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    nixpkgs-pi.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs = {
    self,
    nixpkgs,
    nixpkgs-pi,
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
    piPackagesOverlay = import ./overlays/pi-packages {};
    piCodingAgentOverlay = final: prev: {
      pi-coding-agent = nixpkgs-pi.legacyPackages.${prev.stdenv.hostPlatform.system}.pi-coding-agent;
    };

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
      inherit (pkgs) pi-vim pi-search pi-search-mcp rpiv-todo pi-subagents plannotator-pi-extension pi-coding-agent;
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
