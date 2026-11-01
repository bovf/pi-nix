{}: final: prev: {
  badwater-gitlab = prev.stdenvNoCC.mkDerivation {
    pname = "badwater-gitlab";
    version = "0.1.0";
    src = ../../pkgs/badwater-gitlab;
    installPhase = ''
      runHook preInstall
      mkdir -p "$out/bin"
      cp -r . "$out/"
      ln -s ${prev.glab}/bin/glab "$out/bin/glab"
      substituteInPlace "$out/references/cli.md" \
        --replace-fail '@GLAB@' '${prev.glab}/bin/glab' \
        --replace-fail '@GLAB_VERSION@' '${prev.glab.version}'
      runHook postInstall
    '';
    passthru.cliPackage = prev.glab;
    meta = {
      description = "Explicit, read-first GitLab CLI skill for Pi's native MCP integration";
      license = prev.lib.licenses.mit;
      platforms = ["x86_64-linux" "aarch64-linux" "aarch64-darwin"];
      mainProgram = "glab";
    };
  };
}
