{}: final: prev: let
  lib = prev.lib;
  node = final.pi-coding-agent.nodejs;
  hostModules = "${final.pi-coding-agent}/lib/pi/node_modules";
  supportedSystems = ["x86_64-linux" "aarch64-linux" "aarch64-darwin"];
  browserSupported = builtins.elem prev.stdenv.hostPlatform.system ["x86_64-linux" "aarch64-linux"];
  runtimeSource = ../../pkgs/badwater-senior-swarm;
  driver = prev.playwright-driver;
  browsers = driver.selectBrowsers {
    withChromium = true;
    withChromiumHeadlessShell = true;
    withFirefox = false;
    withWebkit = false;
    withFfmpeg = false;
  };
  axe = prev.stdenvNoCC.mkDerivation {
    pname = "badwater-senior-swarm-axe-core";
    version = "4.14.0";
    src = prev.fetchurl {
      url = "https://registry.npmjs.org/axe-core/-/axe-core-4.14.0.tgz";
      hash = "sha512-9WTZxEjsZ7b13TH8JPmbV2z8CHbl80/2hm3XPEG4JgNdQLK81IBRXmSxHfMAOkSqQeRxT/0dwNDz2GOm3zzpcQ==";
    };
    sourceRoot = "package";
    installPhase = ''
      mkdir -p "$out"
      cp axe.min.js LICENSE README.md "$out/"
    '';
    meta.license = lib.licenses.mpl20;
  };
in
  {
    badwater-senior-swarm = prev.stdenvNoCC.mkDerivation {
      pname = "badwater-senior-swarm";
      version = "0.1.0";
      src = runtimeSource;
      nativeBuildInputs = [prev.makeWrapper];
      installPhase = ''
        runHook preInstall
        mkdir -p "$out"
        cp -r . "$out/"
        # Standalone native ESM must resolve the very same modules as the host Pi.
        test ! -e "$out/node_modules"
        mkdir -p "$out/node_modules/@earendil-works"
        for peer in pi-coding-agent pi-ai pi-agent-core pi-tui; do
          test -d "${hostModules}/@earendil-works/$peer"
          ln -s "${hostModules}/@earendil-works/$peer" "$out/node_modules/@earendil-works/$peer"
        done
        test -d "${hostModules}/typebox"
        ln -s "${hostModules}/typebox" "$out/node_modules/typebox"
        ln -s ${final.pi-subagents} "$out/node_modules/pi-subagents"
        cat > "$out/paths.json" <<'JSON'
        ${builtins.toJSON {
          node = "${node}/bin/node";
          git = "${prev.git}/bin/git";
          shell = "${prev.bash}/bin/bash";
          runtimePath = lib.makeBinPath (lib.optional prev.stdenv.hostPlatform.isLinux prev.procps);
          browser =
            if browserSupported
            then "${final.badwater-senior-swarm-browser}/bin/badwater-senior-swarm-browser"
            else null;
          pi = "${hostModules}/@earendil-works/pi-coding-agent";
          subagents = "${final.pi-subagents}";
        }}
        JSON
        test -f "$out/package.json"
        test -f "$out/extension.mjs"
        test -f "$out/cli.mjs"
        mkdir -p "$out/bin"
        makeWrapper ${node}/bin/node "$out/bin/badwater-senior-swarm" --add-flags "$out/cli.mjs"
        runHook postInstall
      '';
      passthru.nodejs = node;
      meta = {
        description = "Approval-gated parent-only senior swarm workflows for Pi";
        # Reference documents retain their own licenses, not a blanket runtime grant.
        license = with lib.licenses; [mit asl20 cc-by-sa-40];
        platforms = supportedSystems;
        mainProgram = "badwater-senior-swarm";
      };
    };
  }
  // lib.optionalAttrs browserSupported {
    badwater-senior-swarm-browser = prev.stdenvNoCC.mkDerivation {
      pname = "badwater-senior-swarm-browser";
      version = "0.1.0";
      dontUnpack = true;
      nativeBuildInputs = [prev.makeWrapper];
      installPhase = ''
        runHook preInstall
        mkdir -p "$out/lib/badwater-senior-swarm-browser" "$out/bin"
        cp ${runtimeSource}/browser.mjs "$out/lib/badwater-senior-swarm-browser/browser.mjs"
        cat > "$out/lib/badwater-senior-swarm-browser/browser-paths.json" <<'JSON'
        ${builtins.toJSON {
          node = "${node}/bin/node";
          bwrap = "${prev.bubblewrap}/bin/bwrap";
          playwright = "${driver}";
          browsers = "${browsers}";
          axe = "${axe}/axe.min.js";
          axeVersion = axe.version;
          fontconfig = prev.makeFontsConf {fontDirectories = [prev.dejavu_fonts];};
        }}
        JSON
        makeWrapper ${node}/bin/node "$out/bin/badwater-senior-swarm-browser" --add-flags "$out/lib/badwater-senior-swarm-browser/browser.mjs"
        runHook postInstall
      '';
      doInstallCheck = true;
      installCheckPhase = ''
        export HOME="$TMPDIR/home"
        mkdir -p "$HOME"
        ${node}/bin/node --test ${runtimeSource}/tests/browser-policy.test.mjs ${runtimeSource}/tests/browser-lifecycle.test.mjs
      '';
      passthru = {inherit node driver browsers axe;};
      meta = {
        description = "Finite private Playwright/axe screenshot and accessibility evidence helper";
        license = with lib.licenses; [mit asl20 mpl20];
        platforms = ["x86_64-linux" "aarch64-linux"];
        mainProgram = "badwater-senior-swarm-browser";
      };
    };
  }
