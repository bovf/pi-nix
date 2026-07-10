{...}: final: prev: {
  pi-coding-agent = prev.buildNpmPackage (finalAttrs: {
    pname = "pi-coding-agent";
    version = "0.80.6";

    src = prev.fetchFromGitHub {
      owner = "earendil-works";
      repo = "pi";
      tag = "v${finalAttrs.version}";
      hash = "sha256-e/wcHruEcBAHDF5tKvwew7LXjVp0eraHh2k+QaL2sCA=";
    };

    npmDepsHash = "sha256-xXEOR0epZcfbXayYGyJdBiFVliamBexqA+1Sd7wlGhU=";
    npmWorkspace = "packages/coding-agent";

    # Skip native module rebuild for unneeded workspaces (e.g. canvas from web-ui).
    npmRebuildFlags = ["--ignore-scripts"];

    nativeBuildInputs = [prev.makeBinaryWrapper];

    buildPhase = ''
      runHook preBuild

      npx tsgo -p packages/ai/tsconfig.build.json
      npx tsgo -p packages/tui/tsconfig.build.json
      npx tsgo -p packages/agent/tsconfig.build.json
      npm run build --workspace=packages/coding-agent

      runHook postBuild
    '';

    postInstall =
      ''
        local nm="$out/lib/node_modules/pi-monorepo/node_modules"

        for ws in @earendil-works/pi-ai:packages/ai \
                  @earendil-works/pi-agent-core:packages/agent \
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
      prev.lib.makeBinPath [
        prev.ripgrep
        prev.fd
      ]
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
