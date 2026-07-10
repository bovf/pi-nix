{hunk}: final: prev: {
  piPackages = {
    hunk-review = {
      name = "hunk-review";
      package = hunk.packages.${final.stdenv.hostPlatform.system}.hunk;
    };

    rpiv-todo = {
      name = "rpiv-todo";
      package = final.rpiv-todo;
    };

    pi-archimedes = {
      name = "pi-archimedes";
      package = final.pi-archimedes;
    };

    pi-subagents = {
      name = "pi-subagents";
      package = final.pi-subagents;
    };

    plannotator-pi-extension = {
      name = "plannotator-pi-extension";
      package = final.plannotator-pi-extension;
    };

    ponytail = {
      name = "ponytail";
      package = final.ponytail;
    };
  };

  ponytail = prev.stdenvNoCC.mkDerivation {
    pname = "ponytail";
    version = "4.8.4";

    src = prev.fetchFromGitHub {
      owner = "DietrichGebert";
      repo = "ponytail";
      tag = "v4.8.4";
      hash = "sha256-1A9GkjCuiqwd6Wxl18CZUGYekxrbeTLVDapNUua8ihg=";
    };

    installPhase = ''
      runHook preInstall
      mkdir -p $out
      cp -r . $out/
      runHook postInstall
    '';

    meta = {
      description = "Lazy senior dev mode for AI agents";
      homepage = "https://github.com/DietrichGebert/ponytail";
      license = prev.lib.licenses.mit;
      platforms = prev.lib.platforms.unix;
    };
  };

  pi-archimedes = prev.buildNpmPackage rec {
    pname = "pi-archimedes";
    version = "1.7.1";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/pi-archimedes/-/pi-archimedes-${version}.tgz";
      hash = "sha512-DXctozJ7dRbuRTNROWtcysolphRzwZ3H8K8hqvyFyNH9NvHTf3iHwvxbOw7m9+h2hoNMuzUrg7dZz+VkhZMIDQ==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-2p0mzNm6bYdR4QRBn/WKLOF6mLrI0eItjXKmU8w4R2U=";
    dontNpmBuild = true;
    npmFlags = ["--legacy-peer-deps" "--omit=dev"];
    npmInstallFlags = ["--legacy-peer-deps" "--omit=dev"];
    npm_config_legacy_peer_deps = "true";

    postPatch = ''
      cp ${../../pkgs/pi-archimedes/package-lock.json} package-lock.json
    '';

    installPhase = ''
      runHook preInstall
      mkdir -p $out
      cp -r . $out/
      runHook postInstall
    '';

    meta = {
      description = "Integrated extension suite for the Pi coding agent";
      homepage = "https://github.com/danielcherubini/pi-archimedes";
      license = prev.lib.licenses.mit;
      platforms = prev.lib.platforms.unix;
    };
  };

  rpiv-todo = prev.buildNpmPackage rec {
    pname = "rpiv-todo";
    version = "1.20.0";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/@juicesharp/rpiv-todo/-/rpiv-todo-${version}.tgz";
      hash = "sha512-+tRVFrR/WVc/78UQm0+w+goAIKNyO28Lzrfr9agnOfccIkk98M0T/hnGY8z1PjYkNDnDk+BETiOYhhLqJvuNcQ==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-nQDJ7UAxSIbPV0uuAzKiDh/0AiAysUF03PNyQjxMfcA=";
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

  plannotator-pi-extension = prev.buildNpmPackage rec {
    pname = "plannotator-pi-extension";
    version = "0.22.0";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/@plannotator/pi-extension/-/pi-extension-${version}.tgz";
      hash = "sha512-EdTTfw5jk8ENz8MILD58/muGlgmFQgiqmD8B7l7KZb32atyB/k36Af+33XKtB/glV2LblfFNImXQF82jo8u1ZA==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-WqXnYLpkuDHqXqO8K5CplFJHHntwgIA/TXrFbKReD44=";
    dontNpmBuild = true;
    npmFlags = ["--legacy-peer-deps" "--omit=dev"];
    npmInstallFlags = ["--legacy-peer-deps" "--omit=dev"];
    npm_config_legacy_peer_deps = "true";

    postPatch = ''
      cp ${../../pkgs/pi-extension/package-lock.json} package-lock.json
    '';

    installPhase = ''
      runHook preInstall
      mkdir -p $out
      cp -r . $out/
      runHook postInstall
    '';

    meta = {
      description = "Plannotator Pi extension for interactive plan and code review annotations";
      homepage = "https://github.com/backnotprop/plannotator";
      license = with prev.lib.licenses; [mit asl20];
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
    npmDepsHash = "sha256-uMhB77yzDw7bn+j7QQYv57TT4IyfZltD9oTEBOSz+Fg=";
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
