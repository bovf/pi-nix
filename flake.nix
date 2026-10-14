{
  description = "Nix flake for pi-coding-agent and related pi extensions";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";

    pi-upstream = {
      url = "github:earendil-works/pi/v1.2.0";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    hunk = {
      url = "github:modem-dev/hunk/v0.23.0";
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
    videoOverlay = import ./overlays/badwater-video {};

    defaultOverlay = final: prev:
      (piVimOverlay final prev)
      // (piSearchOverlay final prev)
      // (piPackagesOverlay final prev)
      // (piCodingAgentOverlay final prev)
      // (videoOverlay final prev);
  in {
    overlays = {
      default = defaultOverlay;
      pi-vim = piVimOverlay;
      pi-search = piSearchOverlay;
      pi-packages = piPackagesOverlay;
      pi-coding-agent = piCodingAgentOverlay;
      badwater-video = videoOverlay;
    };

    packages = forAllSystems (system: let
      pkgs = import nixpkgs {
        inherit system;
        overlays = [self.overlays.default];
        config.allowUnfree = true;
      };
    in
      {
        inherit (pkgs) pi-vim pi-search pi-search-mcp rpiv-todo pi-archimedes pi-subagents remote-pi plannotator-pi-extension ponytail pi-wait-what pi-lsp pi-chrome-devtools pi-btw pi-goal pi-coding-agent;
        hunk-review = pkgs.piPackages.hunk-review.package;
        default = pkgs.pi-coding-agent;
      }
      // nixpkgs.lib.optionalAttrs pkgs.stdenv.hostPlatform.isLinux {
        inherit (pkgs) badwater-video badwater-craft-mcp;
      });

    # This package runs the footer checks during its build, not only via flake check.
    checks = forAllSystems (system: let
      pkgs = nixpkgs.legacyPackages.${system};
      core = self.packages.${system}.pi-coding-agent;
    in
      {
        openai-context =
          pkgs.runCommand "pi-openai-context-tests" {
            nativeBuildInputs = [core.nodejs pkgs.coreutils];
          } ''
            export HOME="$TMPDIR/home" PI_OFFLINE=1
            mkdir -p "$HOME" "$TMPDIR/work"
            cd "$TMPDIR/work"
            timeout 120 node ${./tests/openai-context.mjs} ${core} ${self.packages.${system}.pi-subagents} ${./overlays/pi-coding-agent/openai-codex-context.json}
            touch "$out"
          '';
        archimedes-footer = self.packages.${system}.pi-archimedes;
      }
      // nixpkgs.lib.optionalAttrs (system != "aarch64-darwin") {
        badwater-video = self.packages.${system}.badwater-video;
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
