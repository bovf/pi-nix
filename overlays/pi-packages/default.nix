{hunk}: final: prev: let
  mkNarumirunaExtension = {
    pname,
    version,
    hash,
    npmDepsHash,
    lockFile,
    description,
    forceEmptyCache ? false,
  }:
    prev.buildNpmPackage rec {
      inherit pname version npmDepsHash forceEmptyCache;

      src = prev.fetchurl {
        url = "https://registry.npmjs.org/@narumitw/${pname}/-/${pname}-${version}.tgz";
        inherit hash;
      };

      sourceRoot = "package";
      dontNpmBuild = true;
      npmFlags = ["--legacy-peer-deps" "--omit=dev"];
      npmInstallFlags = ["--legacy-peer-deps" "--omit=dev"];
      npm_config_legacy_peer_deps = "true";

      postPatch = ''
        cp package.json package.json.upstream
        ${prev.jq}/bin/jq 'del(.devDependencies, .peerDependencies)' package.json > package.json.nix
        mv package.json.nix package.json
        cp ${lockFile} package-lock.json
      '';

      installPhase = ''
        runHook preInstall
        mv package.json.upstream package.json
        rm package-lock.json
        mkdir -p $out
        cp -r . $out/
        runHook postInstall
      '';

      meta = {
        inherit description;
        homepage = "https://github.com/narumiruna/pi-extensions/tree/main/extensions/${pname}";
        license = prev.lib.licenses.mit;
        platforms = prev.lib.platforms.unix;
      };
    };
in {
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

    remote-pi = {
      name = "remote-pi";
      package = final.remote-pi;
    };

    plannotator-pi-extension = {
      name = "plannotator-pi-extension";
      package = final.plannotator-pi-extension;
    };

    ponytail = {
      name = "ponytail";
      package = final.ponytail;
    };

    pi-wait-what = {
      name = "pi-wait-what";
      package = final.pi-wait-what;
    };

    pi-lsp = {
      name = "pi-lsp";
      package = final.pi-lsp;
    };

    pi-chrome-devtools = {
      name = "pi-chrome-devtools";
      package = final.pi-chrome-devtools;
    };

    pi-btw = {
      name = "pi-btw";
      package = final.pi-btw;
    };

    pi-goal = {
      name = "pi-goal";
      package = final.pi-goal;
    };
  };

  pi-wait-what = mkNarumirunaExtension {
    pname = "pi-wait-what";
    version = "0.13.1";
    hash = "sha512-X7MfQNMUmqsO+U4fuPwR+Kdva574iLh+tyo/jHrun19JXjvU+r7Db9LLfpNfX2+4q6aRaGZkSviMa3mBeKcN9Q==";
    npmDepsHash = "sha256-+S6XWIYt6mP8huazbn49z2h60EuGDbmlmuCnWE5uvmY=";
    lockFile = ../../pkgs/pi-wait-what/package-lock.json;
    description = "Pause Pi and ask it to explain surprising actions";
    forceEmptyCache = true;
  };

  pi-lsp = mkNarumirunaExtension {
    pname = "pi-lsp";
    version = "0.22.0";
    hash = "sha512-mYwVY5yv38RKJWkan9Rxspdj3Ko4aZu9FKqs615CT6N2iC7wM12kcqSVaBxD0rnItD27l6PGIXSvMdddKPP0QQ==";
    npmDepsHash = "sha256-iuYi4xTtfkp21bwKcCQMPsZZoyDqT5sKmPEPtPTXK5o=";
    lockFile = ../../pkgs/pi-lsp/package-lock.json;
    description = "Configurable language-server tools for Pi";
  };

  pi-chrome-devtools = mkNarumirunaExtension {
    pname = "pi-chrome-devtools";
    version = "0.20.0";
    hash = "sha512-iqwAD5vCtMD3oSEOWISXTduhBEdB8cCiQf/YOrJd5cUoVKP/F+RGyzspAmhdYN0pxwnVEhWav+bBiuAaiEnbcQ==";
    npmDepsHash = "sha256-u7eXE/bCms2zvGeVVi1QU8Emikg7hBBEC7G7TqYZvE4=";
    lockFile = ../../pkgs/pi-chrome-devtools/package-lock.json;
    description = "Chrome DevTools Protocol tools for Pi";
  };

  pi-btw = mkNarumirunaExtension {
    pname = "pi-btw";
    version = "0.20.0";
    hash = "sha512-Di94do5mN9MU9o1JFzxYIij4/berFwUrFus7JoRJpEALr1Ifci94/6iEtnJJdBD8VJcrrRIBbneBrtlQNwX/lQ==";
    npmDepsHash = "sha256-bqCE53uetfKmOr7pg8s1aRd9wW/CevF9zR4qQ6UoFPM=";
    lockFile = ../../pkgs/pi-btw/package-lock.json;
    description = "Side-question command for Pi";
    forceEmptyCache = true;
  };

  pi-goal = mkNarumirunaExtension {
    pname = "pi-goal";
    version = "0.20.0";
    hash = "sha512-a3gbJfByQmjY6/W4WeRAh3aWB4freRcWJBasrzAKuUiPfewj5NUTkZTcFWc9xeyRwLycp7zULFXaXyjD71tygw==";
    npmDepsHash = "sha256-ko9mkbkQ9HkqdazeC29+RZ2Q+nljbPFPIO1KT2+9mM8=";
    lockFile = ../../pkgs/pi-goal/package-lock.json;
    description = "Persistent goal mode for Pi";
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
    npmDepsHash = "sha256-PZ3Hal3J3a5QOpjj+lg2PsugCbYaMwgHPp+mjemMOYY=";
    dontNpmBuild = true;
    npmFlags = ["--legacy-peer-deps" "--omit=dev"];
    npmInstallFlags = ["--legacy-peer-deps" "--omit=dev"];
    npm_config_legacy_peer_deps = "true";

    postPatch = ''
      cp ${../../pkgs/pi-archimedes/package-lock.json} package-lock.json
    '';

    postFixup = ''
      substituteInPlace "$out/src/index.ts" \
        --replace-fail '  // Register image paste (shortcuts, input handler, preview renderer)' '  // ponytail: Pi core owns cross-platform clipboard images and draft removal.' \
        --replace-fail '  registerImagePaste(pi);' "" \
        --replace-fail '  // Register subagent tool' '  // ponytail: pi-subagents owns delegation; duplicate tool registration is fatal.' \
        --replace-fail '  registerSubagent(pi);' "" \
        --replace-fail '  // Register /agents command' "" \
        --replace-fail '  registerAgentsCommand(pi);' ""
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
    version = "0.23.1";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/@plannotator/pi-extension/-/pi-extension-${version}.tgz";
      hash = "sha512-YjzIsQ+nv+MFe+KItLlGRf/OIaG6m5/oIBLcQkKTM8hmDvjtXraRqTo91GRWzJ3s3fQeXcfzQFBc4APaUYkTsg==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-dS0lJ37/81e+Q7E32UnYuij7vriKGFLttDr4Atpq7qI=";
    npmDepsFetcherVersion = 2;
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
    version = "0.35.1";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/pi-subagents/-/pi-subagents-${version}.tgz";
      hash = "sha512-nIH6liO541FZ1RoeEu58Ligd59tiNw0/ODPgHh7uvx9Dk4UpWH08F84/l1+hXCzUgC85OCmyVtngWkZjcK94Cg==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-sSyUw1DiGxLyNoKbKiVQE9UGFEZdbVuBicka8Lb0+p4=";
    npmDepsFetcherVersion = 2;
    dontNpmBuild = true;
    npmFlags = ["--legacy-peer-deps" "--omit=dev"];
    npmInstallFlags = ["--legacy-peer-deps" "--omit=dev"];
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

  remote-pi = prev.buildNpmPackage rec {
    pname = "remote-pi";
    version = "0.5.5";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/remote-pi/-/remote-pi-${version}.tgz";
      hash = "sha512-HC8axMzCTb2//SLI+rZugIMdHym8VUgsa0a7dGdaPe+vW+YmyJ6ct3Vvfz/iSsqzzLpbA9QjQ4mgJfZNbIwe6Q==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-B+RiYCD/c8qj9Al33o5QOes4DsU446CVxcQNUnb7vaY=";
    npmDepsFetcherVersion = 2;
    dontNpmBuild = true;
    npmFlags = ["--legacy-peer-deps" "--omit=dev"];
    npmInstallFlags = ["--legacy-peer-deps" "--omit=dev"];
    npm_config_legacy_peer_deps = "true";

    postPatch = ''
      cp package.json package.json.upstream
      ${prev.jq}/bin/jq 'del(.devDependencies)' package.json > package.json.nix
      mv package.json.nix package.json
      cp ${../../pkgs/remote-pi/package-lock.json} package-lock.json
    '';

    installPhase = ''
      runHook preInstall
      mv package.json.upstream package.json
      rm package-lock.json
      mkdir -p $out
      cp -r . $out/
      runHook postInstall
    '';

    meta = {
      description = "Mobile remote control and local agent mesh for Pi";
      homepage = "https://github.com/jacobaraujo7/remote_pi";
      license = prev.lib.licenses.mit;
      platforms = prev.lib.platforms.unix;
    };
  };
}
