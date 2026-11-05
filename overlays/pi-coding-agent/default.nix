{pi-upstream, ...}: final: prev: let
  # Upstream's offline build already compiles these libraries; only pack its artifacts.
  core = prev.callPackage "${pi-upstream}/nix/package.nix" {
    source = pi-upstream;
    # Pi 1.5's install lock adds schema but its recipe omits the compiled override.
    importNpmLock =
      prev.importNpmLock
      // {
        __functor = _: args:
          prev.importNpmLock (args
            // prev.lib.optionalAttrs (args ? packageSourceOverrides) (
              assert prev.lib.assertMsg (!(args.packageSourceOverrides ? "node_modules/@earendil-works/pi-schema")) "Upstream now supplies pi-schema; retire its local artifact bridge"; let
                codingArchive = args.packageSourceOverrides."node_modules/@earendil-works/pi-coding-agent";
                compiled = prev.lib.strings.addContextFrom codingArchive (builtins.dirOf codingArchive);
              in {
                packageSourceOverrides =
                  args.packageSourceOverrides
                  // {
                    "node_modules/@earendil-works/pi-schema" = "${compiled}/schema.tgz";
                  };
              }
            ));
      };
    stdenv =
      prev.stdenv
      // {
        mkDerivation = attrs:
          prev.stdenv.mkDerivation (attrs
            // prev.lib.optionalAttrs (attrs.pname == "pi-workspace-packages") (
              assert builtins.length (prev.lib.splitString "pack_package packages/coding-agent coding-agent" attrs.installPhase) == 2;
              assert prev.lib.assertMsg (builtins.length (prev.lib.splitString "pack_package packages/schema schema" attrs.installPhase) == 1) "Upstream now packs pi-schema; retire its local artifact bridge"; {
                installPhase =
                  prev.lib.replaceStrings ["pack_package packages/coding-agent coding-agent"] [
                    ''
                      pack_package packages/coding-agent coding-agent
                      pack_package packages/schema schema
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
    postInstallCheck =
      (old.postInstallCheck or "")
      + ''
        ${prev.nodejs_22}/bin/node ${../../tests/core-schema.mjs} "$out" ${prev.lib.escapeShellArg core.version}
      '';
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
