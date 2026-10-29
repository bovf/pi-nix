{}: final: prev: {
  rea = prev.buildNpmPackage rec {
    pname = "rea";
    version = "6.8.0";
    src = prev.fetchurl {
      url = "https://registry.npmjs.org/rea-agents/-/rea-agents-${version}.tgz";
      hash = "sha512-9QDeRnGqEDzABZyr04eLnBXBv/c6I9/TWu/6M0MD4pEfkySI/BIgwTODIbAReX3C1x6hjw9+Jlx4A2yUSPZ9ww==";
    };
    nodejs = prev.nodejs_22;
    sourceRoot = "package";
    npmDepsHash = "sha256-I77F7iVdOfJabNXtQQLLOerp1jw5Qag6922AKD/CoSo=";
    dontNpmBuild = true;
    npmFlags = ["--ignore-scripts" "--omit=dev" "--legacy-peer-deps"];
    nativeBuildInputs = [prev.makeWrapper prev.jq prev.autoPatchelfHook];
    buildInputs = [prev.stdenv.cc.cc.lib];
    postPatch = ''
      ${prev.jq}/bin/jq -f ${../../pkgs/rea/package-filter.jq} package.json > package.json.nix
      mv package.json.nix package.json
      rm -f npm-shrinkwrap.json
      cp ${../../pkgs/rea/package-lock.json} package-lock.json
    '';
    installPhase = ''
      runHook preInstall
      mkdir -p "$out/lib/rea" "$out/bin" "$out/share/rea"
      cp -r dist bridge scripts skills third_party licenses package.json LICENSE DISCLAIMER.md THIRD_PARTY_NOTICES.md README.md node_modules "$out/lib/rea/"
      cp ${../../pkgs/rea/NOTICE.md} "$out/share/rea/NOTICE.md"
      cp ${../../pkgs/rea/package-lock.json} "$out/share/rea/package-lock.json"
      ln -s "$out/lib/rea/skills" "$out/share/rea/skills"
      substituteInPlace "$out/lib/rea/skills/reverse-engineer-anything/SKILL.md" \
        --replace-fail '# REA' '# REA

      Nix distribution: use the installed `rea` command, never `npx`, global npm,
      setup, update, uninstall or runtime acquisition. Agent registration and skill
      ownership belong to the declarative Home Manager policy. This x86_64-linux
      bundle supplies Ghidra/JDK, Rizin and GNU objdump plus built-in static tools.
      Frida, Android, firmware engines, browsers, capture/signal backends and
      pwntools/pwndbg/GDB are omitted. The full advertised catalog is not proof
      every backend is installed. Never attach, execute targets, access devices,
      capture traffic or relax permissions without separate explicit approval.
      These distribution constraints override acquisition/setup advice below.'
      makeWrapper ${nodejs}/bin/node "$out/bin/rea" \
        --add-flags "$out/lib/rea/scripts/rea.mjs" \
        --prefix PATH : ${prev.lib.makeBinPath [prev.procps prev.util-linux prev.binutils prev.rizin prev.openjdk21 prev.bash]} \
        --set-default GHIDRA_INSTALL_DIR ${prev.ghidra}/lib/ghidra \
        --set-default JAVA_HOME ${prev.openjdk21} \
        --set-default REA_ANALYSIS_PROVIDER ghidra \
        --set PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD 1
      # Nix owns installation/configuration; these upstream commands mutate it.
      substituteInPlace "$out/lib/rea/scripts/rea.mjs" \
        --replace-fail 'const isShellCompletion =' 'const nixCommand = builtinArguments.splitIncurBuiltinArguments(builtinArguments.normalizeCliArguments(args)).command;
      // Match Incur builtinIdx: MCP registration also accepts one leading CLI name.
      const nixRegistrationCommand = nixCommand[0] === "rea" ? nixCommand.slice(1) : nixCommand;
      if (["setup", "update", "uninstall"].includes(nixCommand[0]) || args.includes("--incur-update-check") || (nixRegistrationCommand[0] === "mcp" && ["add", "remove"].includes(nixRegistrationCommand[1]))) {
        process.stderr.write("REA installation and agent configuration are managed by Nix; use the owning flake/policy instead.\\n");
        process.exit(1);
      }
      const isShellCompletion ='
      runHook postInstall
    '';
    doInstallCheck = true;
    installCheckPhase = ''
      runHook preInstallCheck
      export HOME="$TMPDIR/rea-home"
      mkdir -p "$HOME"
      cd "$HOME"
      cp ${../../tests/rea.mjs} ./rea.mjs
      cp ${../../tests/mcp-stdio.mjs} ./mcp-stdio.mjs
      env -i HOME="$HOME" TMPDIR="$TMPDIR" PATH=${prev.lib.makeBinPath [nodejs prev.coreutils prev.bash]} \
        ${nodejs}/bin/node ./rea.mjs "$out"
      env -i HOME="$HOME" TMPDIR="$TMPDIR" PATH=${prev.lib.makeBinPath [nodejs prev.coreutils prev.bash]} \
        ${nodejs}/bin/node ${../../tests/rea-native.mjs} "$out" ${prev.binutils}
      runHook postInstallCheck
    '';
    passthru = {
      inherit nodejs;
      runtimeBackends = [prev.ghidra prev.openjdk21 prev.rizin prev.binutils prev.procps prev.util-linux];
      skillRelativePath = "share/rea/skills/reverse-engineer-anything";
      mcpArgs = ["mcp"];
    };
    meta = {
      description = "Reverse engineering CLI and stdio MCP with free native/static Linux backends";
      homepage = "https://github.com/morluto/rea";
      license = prev.lib.licenses.mit;
      # The selected Ghidra archive supplies only the Linux x86-64 decompiler.
      platforms = ["x86_64-linux"];
      mainProgram = "rea";
    };
  };
}
