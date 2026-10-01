{...}: final: prev: {
  pi-coding-agent = prev.buildNpmPackage (finalAttrs: {
    pname = "pi-coding-agent";
    version = "0.99.2";

    src = prev.fetchurl {
      url = "https://github.com/earendil-works/pi/archive/refs/tags/v${finalAttrs.version}.tar.gz";
      hash = "sha256-4yoWwWsM28phRS225YQDC55Z/Bsqop4gOpPthbVJC+g=";
    };

    npmDepsHash = "sha256-eKghIpCAKawZm0Uf2iG6y1fz21Z5jNnMiAFJ5Quj3GI=";
    npmWorkspace = "packages/coding-agent";

    # Git tags omit generated model data; use the matching published catalog offline.
    modelData = prev.fetchurl {
      url = "https://registry.npmjs.org/@earendil-works/pi-ai/-/pi-ai-${finalAttrs.version}.tgz";
      hash = "sha512-9RFOEdY+ZTJ1AI+UuAFs4RM0tF2Tje/R/CEv9gWTJHt0iTu8XHZs64U/EIZxNSllFmec/4HfwsOxYj1qQek9bg==";
    };
    postPatch = ''
      tar -xzf ${finalAttrs.modelData} --strip-components=3 -C packages/ai/src/providers package/dist/providers/data
    '';

    # Skip native module rebuild for unneeded workspaces (e.g. canvas from web-ui).
    npmRebuildFlags = ["--ignore-scripts"];

    nativeBuildInputs = [prev.makeBinaryWrapper];

    buildPhase = ''
      runHook preBuild

      npm run build:offline

      runHook postBuild
    '';

    postInstall =
      ''
        local nm="$out/lib/node_modules/pi-monorepo/node_modules"

        for ws in @earendil-works/chord:packages/chord \
                  @earendil-works/pi-telemetry:packages/telemetry \
                  @earendil-works/pi-ai:packages/ai \
                  @earendil-works/pi-codemode:packages/codemode \
                  @earendil-works/pi-mcp:packages/mcp \
                  @earendil-works/pi-durable:packages/durable \
                  @earendil-works/pi-agent-core:packages/agent \
                  @earendil-works/pi-session-backend-sqlite-node:packages/session-backends/sqlite-node \
                  @earendil-works/pi-protocol:packages/protocol \
                  @earendil-works/pi-client:packages/client \
                  @earendil-works/pi-server:packages/server \
                  @earendil-works/pi-tui:packages/tui; do
          IFS=: read -r pkg src <<< "$ws"
          rm "$nm/$pkg"
          cp -r "$src" "$nm/$pkg"
        done

        find "$nm" -type l -lname '*/packages/*' -delete
        find "$nm/.bin" -xtype l -delete
      ''
      + prev.lib.optionalString prev.stdenvNoCC.hostPlatform.isDarwin ''
        rm -rf \
          "$nm/@anthropic-ai/sandbox-runtime/dist/vendor/seccomp" \
          "$nm/@anthropic-ai/sandbox-runtime/vendor/seccomp"
      '';

    postFixup = "wrapProgram $out/bin/pi --prefix PATH : ${
      prev.lib.makeBinPath (
        [
          prev.ripgrep
          prev.fd
        ]
        ++ prev.lib.optionals prev.stdenv.hostPlatform.isLinux [
          prev.wl-clipboard
          prev.xclip
        ]
      )
    }";

    doInstallCheck = true;
    nativeInstallCheckInputs = [
      prev.writableTmpDirAsHomeHook
      prev.versionCheckHook
    ];
    versionCheckKeepEnvironment = ["HOME"];
    versionCheckProgram = "${placeholder "out"}/bin/pi";
    versionCheckProgramArg = "--version";

    meta = {
      description = "Coding agent CLI with read, bash, edit, write tools and session management";
      homepage = "https://pi.dev/";
      downloadPage = "https://www.npmjs.com/package/@earendil-works/pi-coding-agent";
      changelog = "https://github.com/earendil-works/pi/blob/main/packages/coding-agent/CHANGELOG.md";
      license = prev.lib.licenses.mit;
      mainProgram = "pi";
      platforms = prev.lib.platforms.unix;
    };
  });
}
