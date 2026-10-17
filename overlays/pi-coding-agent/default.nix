{pi-upstream, ...}: final: prev: let
  # Upstream's offline build already compiles these libraries; only pack its artifacts.
  core = prev.callPackage "${pi-upstream}/nix/package.nix" {
    source = pi-upstream;
    stdenv =
      prev.stdenv
      // {
        mkDerivation = attrs:
          prev.stdenv.mkDerivation (attrs
            // prev.lib.optionalAttrs (attrs.pname == "pi-workspace-packages") (
              assert builtins.length (prev.lib.splitString "pack_package packages/coding-agent coding-agent" attrs.installPhase) == 2; {
                installPhase =
                  prev.lib.replaceStrings ["pack_package packages/coding-agent coding-agent"] [
                    ''
                      pack_package packages/coding-agent coding-agent
                      pack_package packages/durable durable
                      pack_package packages/chord chord''
                  ]
                  attrs.installPhase;
              }
            ));
      };
  };
  # Parsing drops Nix string context; restore it from the complete upstream metadata.
  lock = core.npmDeps.packageLock;
  tarball = (builtins.fromJSON (builtins.unsafeDiscardStringContext lock)).packages."node_modules/@earendil-works/pi-coding-agent".resolved;
  workspacePackages = prev.lib.strings.addContextFrom lock (builtins.dirOf (prev.lib.removePrefix "file:" tarball));
in {
  pi-coding-agent = core.overrideAttrs (old: {
    passthru =
      (old.passthru or {})
      // {
        inherit workspacePackages;
        openaiCodexContextWindows = builtins.fromJSON (builtins.readFile ./openai-codex-context.json);
        nodejs = prev.nodejs_22;
      };
    postInstall =
      (old.postInstall or "")
      + ''
        # Durable still imports the compiled Chord library even though the CLI no longer does.
        for workspace in durable chord; do
          name="pi-$workspace"
          if [ "$workspace" = chord ]; then name=chord; fi
          target="$out/lib/pi/node_modules/@earendil-works/$name"
          mkdir -p "$target"
          tar -xzf ${workspacePackages}/$workspace.tgz --strip-components=1 -C "$target"
        done
      '';
  });
}
