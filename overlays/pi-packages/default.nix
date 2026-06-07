{...}: final: prev: {
  piPackages = {
    rpiv-todo = {
      name = "rpiv-todo";
      package = final.rpiv-todo;
    };

    pi-subagents = {
      name = "pi-subagents";
      package = final.pi-subagents;
    };
  };

  rpiv-todo = prev.buildNpmPackage rec {
    pname = "rpiv-todo";
    version = "1.18.2";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/@juicesharp/rpiv-todo/-/rpiv-todo-${version}.tgz";
      hash = "sha512-YQ7jex+AcS7nh3b6cIhYZhBpXx0Z91x/93TQSMFj4Tpxrob5I8zHST72FuWCmL6QCVMHZ2rGB8tGBTF7drIIPw==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-d7js6rHYe5Eh4i5cXuk6O3qat3cEVAvWww7Xb4pgwqc=";
    dontNpmBuild = true;
    npmFlags = ["--legacy-peer-deps"];
    npmInstallFlags = ["--legacy-peer-deps"];
    npm_config_legacy_peer_deps = "true";

    postPatch = ''
      cp ${../../pkgs/rpiv-todo/package-lock.json} package-lock.json
    '';

    installPhase = ''
      runHook preInstall
      mkdir -p $out
      cp -r . $out/
      runHook postInstall
    '';

    meta = {
      description = "Pi todo extension package";
      homepage = "https://pi.dev/packages/@juicesharp/rpiv-todo";
      license = prev.lib.licenses.mit;
      platforms = prev.lib.platforms.unix;
    };
  };

  pi-subagents = prev.buildNpmPackage rec {
    pname = "pi-subagents";
    version = "0.28.0";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/pi-subagents/-/pi-subagents-${version}.tgz";
      hash = "sha512-EWgQphVqH7BWJFNiWdyOCa8uqwr/aWkm9OyhItFiIJfpmdY4mGUlZ2VK1z3UP6XfVAmidtGd0MsnyhuFTxAm0A==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-YTzN3feIMqj/8hmyEPGzI94LZcrELIEUCL1vyY0dXjQ=";
    dontNpmBuild = true;
    npmFlags = ["--legacy-peer-deps"];
    npmInstallFlags = ["--legacy-peer-deps"];
    npm_config_legacy_peer_deps = "true";

    postPatch = ''
      cp ${../../pkgs/pi-subagents/package-lock.json} package-lock.json
    '';

    installPhase = ''
      runHook preInstall
      mkdir -p $out
      cp -r . $out/
      runHook postInstall
    '';

    meta = {
      description = "Pi extension for delegating tasks to subagents";
      homepage = "https://github.com/nicobailon/pi-subagents";
      license = prev.lib.licenses.mit;
      platforms = prev.lib.platforms.unix;
    };
  };
}
