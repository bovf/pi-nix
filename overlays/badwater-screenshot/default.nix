{}: final: prev:
prev.lib.optionalAttrs prev.stdenv.hostPlatform.isLinux (let
  python = prev.python3.withPackages (ps: [ps.mcp ps.pillow]);
in {
  badwater-screenshot = prev.stdenvNoCC.mkDerivation {
    pname = "badwater-screenshot";
    version = "0.1.0";
    src = ../../pkgs/badwater-screenshot;
    nativeBuildInputs = [prev.makeWrapper];
    installPhase = ''
      runHook preInstall
      mkdir -p "$out/bin"
      cp -r . "$out/"
      cat > "$out/paths.json" <<'JSON'
      ${builtins.toJSON {
        browser = "${final.badwater-senior-swarm-browser}/bin/badwater-senior-swarm-browser";
        niri = "${prev.niri}/bin/niri";
        grim = "${prev.grim}/bin/grim";
        spectacle = "${prev.kdePackages.spectacle}/bin/spectacle";
        kdotool = "${prev.kdotool}/bin/kdotool";
      }}
      JSON
      makeWrapper ${python}/bin/python "$out/bin/badwater-screenshot" \
        --add-flags "-s $out/server.py" --unset PYTHONPATH --set PYTHONNOUSERSITE 1
      runHook postInstall
    '';
    passthru = {
      pythonPackage = python;
      cliPackage = prev.runCommand "badwater-screenshot-cli" {} ''
        mkdir -p "$out/bin"
        ln -s ${final.badwater-screenshot}/bin/badwater-screenshot "$out/bin/badwater-screenshot"
      '';
    };
    meta = {
      description = "Permission-first private screenshot MCP and skill with isolated web capture";
      license = prev.lib.licenses.mit;
      platforms = ["x86_64-linux" "aarch64-linux"];
      mainProgram = "badwater-screenshot";
    };
  };
})
