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
    version = "0.49.8";
    hash = "sha512-Djrm0BBmbITmKUv2OtrPUACbP2j1GA7DQ4n/P/mZLf++s6Vv4fMMJUPvrQ01UtnaIQ7XzMCKzWrOyrJatyOGSw==";
    npmDepsHash = "sha256-SDWNmMZApZt9Tg3YM8aqOEYxFdq/uEZEhFtrxUqdYbs=";
    lockFile = ../../pkgs/pi-lsp/package-lock.json;
    description = "Configurable language-server tools for Pi";
    forceEmptyCache = true;
  };

  pi-chrome-devtools = mkNarumirunaExtension {
    pname = "pi-chrome-devtools";
    version = "0.53.4";
    hash = "sha512-okQCIqSRBQwKcFn8YqEaaGIx4l533cdx4VMUJWP2H7P54Zq5rbZm33nz+9jvBKzuwgpeyceQgTqX913Xp9ZQag==";
    npmDepsHash = "sha256-0NqsB5RIgzTjUdyvPYQFZ10xKsniGljC7FLT4mjX2t4=";
    lockFile = ../../pkgs/pi-chrome-devtools/package-lock.json;
    description = "Chrome DevTools Protocol tools for Pi";
  };

  pi-btw = mkNarumirunaExtension {
    pname = "pi-btw";
    version = "0.60.3";
    hash = "sha512-Kvnq9otDG4Tt1vWaLC4NGDXt73iVMvwoOIYeuk8//YsB47QMAUjEGDFu6Ws5MKPjdcnApkKzkJhfSveLbqjJTQ==";
    npmDepsHash = "sha256-wNYByMeBW1/GsgzzyIkFWxXiPwoAGxc5GKNX5o46j7c=";
    lockFile = ../../pkgs/pi-btw/package-lock.json;
    description = "Side-question command for Pi";
    forceEmptyCache = true;
  };

  pi-goal = mkNarumirunaExtension {
    pname = "pi-goal";
    version = "0.54.8";
    hash = "sha512-ba165WkOdBEQNYgjTa2MHgRtOh/hTLveObPzdoE29FOrfktymcBlayEHoXd9Jjw44VQ8bX7cq6V57zp0rJLVgQ==";
    npmDepsHash = "sha256-VYGGaahNOg0RjHSmYYkAbhXVjyqDkadPHbILkkmRdi4=";
    lockFile = ../../pkgs/pi-goal/package-lock.json;
    description = "Persistent goal mode for Pi";
  };

  ponytail = prev.stdenvNoCC.mkDerivation {
    pname = "ponytail";
    version = "4.10.0";

    src = prev.fetchFromGitHub {
      owner = "DietrichGebert";
      repo = "ponytail";
      tag = "v4.10.0";
      hash = "sha256-PES5XrSYx0VBXWVHEDRykGy0SAmJfV/luzy8Gfg0aAQ=";
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
    version = "2.7.3";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/pi-archimedes/-/pi-archimedes-${version}.tgz";
      hash = "sha512-YLJfnG4LDBxnfva/K2U3fuQRfGtmJ5Ntc54RkeELdKnAPv2q9FoGu81mWZR1H1ZXxIZwOEyPQgINPgAVmfYLmw==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-iysXjUt1p39NPjdlrLpzFFal7CSf6dKLf9TnVMqvfpQ=";
    dontNpmBuild = true;
    npmFlags = ["--legacy-peer-deps" "--omit=dev"];
    npmInstallFlags = ["--legacy-peer-deps" "--omit=dev"];
    npm_config_legacy_peer_deps = "true";

    postPatch = ''
      cp ${../../pkgs/pi-archimedes/package-lock.json} package-lock.json
    '';

    postFixup = ''
      substituteInPlace "$out/src/index.ts" \
        --replace-fail 'isPluginEnabled("image-paste")' 'false /* Pi core owns clipboard image handling. */' \
        --replace-fail 'isPluginEnabled("subagent")' 'false /* pi-subagents owns delegation. */'
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
    version = "2.10.1";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/@juicesharp/rpiv-todo/-/rpiv-todo-${version}.tgz";
      hash = "sha512-3VvPztpStw9bp99Iq2z6IsbHL7fGpOY0ugTTE7fzSRipgQY3LkdazuBK6TnKr4jaqungHNbAoUF7e/6gsTz8eg==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-zx4JtKcjgm+Ps4cN1nigqMhMwcljQrvpB01wXq/Bo4w=";
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
    version = "0.27.16";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/@plannotator/pi-extension/-/pi-extension-${version}.tgz";
      hash = "sha512-LfS/EkMD4b+Dzu2kKp/2YORqH27dVbRXhaLYbzqQaK1AtMPexPvBPebZQs4xXBUveanTkYkBKTfp7uT8VeQ5jQ==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-grJRpTZ6WaU7HuBZRa35p0huumL9fPWAJ/62JBqvn2o=";
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
    version = "0.70.0";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/pi-subagents/-/pi-subagents-${version}.tgz";
      hash = "sha512-UkGCym5fFKc1VGRzzE8F2govFwez7zvCOHNV0o+LnNwI/y6QbZNo3U6kIeK9hdBHGAL3e5a+UGiROc4mZR/8lg==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-e9+UAh4r5VQyqPiMdN2Dne68oK+r22UQWynCtxobE38=";
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
    version = "0.7.0";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/remote-pi/-/remote-pi-${version}.tgz";
      hash = "sha512-L2kMTFiuqn5j6NU+Re7M1bOMeRJGBsyp8IrlTSWFF7H7JHzjtBjnOMbCOMuNlN4vkeLLYURXXbsrOCOrE6b4hQ==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-OpM27hdoisnHfQHglfWO7utpvgf202szfkA8LSq8pnU=";
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
