{...}:
# DuckDuckGo web search for pi. Ships:
#   pi-search       — thin CLI wrapper around ddgr --json
#   pi-search-mcp   — stdio MCP server exposing the `web_search` tool
final: prev: let
  py = prev.python3.pkgs;

  pi-search = prev.writeShellApplication {
    name = "pi-search";
    runtimeInputs = [prev.ddgr];
    text = ''
      MAX="''${PI_SEARCH_MAX:-10}"
      ARGS=()
      while [ $# -gt 0 ]; do
        case "$1" in
          --max) MAX="$2"; shift 2 ;;
          --max=*) MAX="''${1#--max=}"; shift ;;
          *) ARGS+=("$1"); shift ;;
        esac
      done
      if [ ''${#ARGS[@]} -eq 0 ]; then
        echo "Usage: pi-search [--max N] <query>" >&2
        exit 2
      fi
      exec ddgr --json -n "$MAX" --noua "''${ARGS[@]}"
    '';
  };

  pythonEnv = prev.python3.withPackages (_: [py.mcp]);

  pi-search-mcp = prev.runCommand "pi-search-mcp-0.1.0" {} ''
    mkdir -p $out/bin
    cat > $out/bin/pi-search-mcp <<'WRAPPER'
    #!/usr/bin/env bash
    export PI_SEARCH_DDGR=${prev.ddgr}/bin/ddgr
    exec ${pythonEnv}/bin/python3 SERVER_PATH "$@"
    WRAPPER
    sed -i "s|SERVER_PATH|${./server.py}|" $out/bin/pi-search-mcp
    chmod +x $out/bin/pi-search-mcp
  '';
in {
  inherit pi-search pi-search-mcp;
}
