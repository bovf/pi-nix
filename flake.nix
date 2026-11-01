{
  description = "Nix flake for pi-coding-agent and related pi extensions";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";

    pi-upstream = {
      url = "github:earendil-works/pi/v1.4.0";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    hunk = {
      url = "github:modem-dev/hunk/v0.24.1";
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
    reaOverlay = import ./overlays/rea {};
    seniorSwarmOverlay = import ./overlays/badwater-senior-swarm {};

    defaultOverlay = final: prev:
      (piVimOverlay final prev)
      // (piSearchOverlay final prev)
      // (piPackagesOverlay final prev)
      // (piCodingAgentOverlay final prev)
      // (videoOverlay final prev)
      // (reaOverlay final prev)
      // (seniorSwarmOverlay final prev);
  in {
    overlays = {
      default = defaultOverlay;
      pi-vim = piVimOverlay;
      pi-search = piSearchOverlay;
      pi-packages = piPackagesOverlay;
      pi-coding-agent = piCodingAgentOverlay;
      badwater-video = videoOverlay;
      rea = reaOverlay;
      badwater-senior-swarm = seniorSwarmOverlay;
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
        badwater-senior-swarm = pkgs.badwater-senior-swarm;
        hunk-review = pkgs.piPackages.hunk-review.package;
        default = pkgs.pi-coding-agent;
      }
      // nixpkgs.lib.optionalAttrs pkgs.stdenv.hostPlatform.isLinux {
        inherit (pkgs) badwater-video badwater-craft-mcp badwater-senior-swarm-browser;
      }
      // nixpkgs.lib.optionalAttrs (system == "x86_64-linux") {
        inherit (pkgs) rea;
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
        badwater-senior-swarm-native =
          pkgs.runCommand "badwater-senior-swarm-native-tests" {
            nativeBuildInputs = [core.nodejs pkgs.git pkgs.bash pkgs.coreutils];
          } ''
            export HOME="$TMPDIR/home" XDG_STATE_HOME="$TMPDIR/state" PI_OFFLINE=1 GIT_CONFIG_NOSYSTEM=1 BADWATER_SENIOR_SWARM_NATIVE_FIXTURE=1
            mkdir -p "$HOME" "$TMPDIR/work"
            cd "$TMPDIR/work"
            timeout --kill-after=5s 120s node ${./pkgs/badwater-senior-swarm/tests/native.mjs} ${self.packages.${system}.badwater-senior-swarm}
            touch "$out"
          '';
        badwater-senior-swarm =
          pkgs.runCommand "badwater-senior-swarm-runtime-tests" {
            nativeBuildInputs = [core.nodejs pkgs.git pkgs.bash pkgs.coreutils];
          } ''
            export HOME="$TMPDIR/home" TMPDIR="$TMPDIR" PI_OFFLINE=1 GIT_CONFIG_NOSYSTEM=1
            mkdir -p "$HOME" "$TMPDIR/work"
            cp -r ${./pkgs/badwater-senior-swarm} "$TMPDIR/work/badwater-senior-swarm"
            chmod -R u+w "$TMPDIR/work/badwater-senior-swarm"
            cd "$TMPDIR/work/badwater-senior-swarm"
            mapfile -t tests < <(find tests -maxdepth 1 -name '*.test.mjs' ! -name 'browser*.test.mjs' | sort)
            test "''${#tests[@]}" -gt 0
            timeout --kill-after=5s 120s node --test "''${tests[@]}"
            touch "$out"
          '';
      }
      // nixpkgs.lib.optionalAttrs (system != "aarch64-darwin") {
        badwater-video = self.packages.${system}.badwater-video;
        badwater-senior-swarm-browser = self.packages.${system}.badwater-senior-swarm-browser;
      }
      // nixpkgs.lib.optionalAttrs (system == "x86_64-linux") {
        rea = self.packages.${system}.rea;
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
