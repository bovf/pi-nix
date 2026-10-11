{
  lib,
  stdenvNoCC,
  python3,
  makeWrapper,
  ffmpeg,
  bubblewrap,
  bash,
  writeText,
}: let
  defaults = writeText "badwater-craft-mcp-defaults.json" (builtins.toJSON {
    bubblewrap = lib.getExe bubblewrap;
    bash = lib.getExe bash;
    toolPath = lib.makeBinPath [ffmpeg bash];
  });
in
  stdenvNoCC.mkDerivation {
    pname = "badwater-craft-mcp";
    version = "0.1.0";
    dontUnpack = true;
    dontBuild = true;
    nativeBuildInputs = [makeWrapper];
    installPhase = ''
      mkdir -p "$out/lib/badwater-craft-mcp" "$out/bin"
      install -m644 ${./craft_mcp.py} "$out/lib/badwater-craft-mcp/craft_mcp.py"
      install -m644 ${./store.py} "$out/lib/badwater-craft-mcp/store.py"
      makeWrapper ${python3}/bin/python3 "$out/bin/badwater-craft-mcp" \
        --add-flags "$out/lib/badwater-craft-mcp/craft_mcp.py" \
        --set BADWATER_CRAFT_DEFAULTS ${defaults} \
        --set PYTHONDONTWRITEBYTECODE 1
    '';
    doInstallCheck = true;
    installCheckPhase = ''
      PYTHONPYCACHEPREFIX="$TMPDIR/bytecode" ${python3}/bin/python3 -m compileall -q "$out/lib/badwater-craft-mcp"
    '';
    meta = {
      description = "Private filesystem/network launcher for verified native Craft stdio MCP";
      mainProgram = "badwater-craft-mcp";
      license = lib.licenses.mit;
      platforms = lib.platforms.linux;
    };
  }
