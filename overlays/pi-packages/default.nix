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
    version = "0.49.4";
    hash = "sha512-RA0XAVAdck8W2gm2Do67C/IrCRUBJkKWPawZg1QqvlfEH9TMZbrGBYOgvGYcnGuRQ3FyxxFgJSq0fbdpMW8KAQ==";
    npmDepsHash = "sha256-XTrhExkeLcvVfYxzZPvAFiutEWkuh4vSYi7SWm/8Igs=";
    lockFile = ../../pkgs/pi-lsp/package-lock.json;
    description = "Configurable language-server tools for Pi";
    forceEmptyCache = true;
  };

  pi-chrome-devtools = mkNarumirunaExtension {
    pname = "pi-chrome-devtools";
    version = "0.50.1";
    hash = "sha512-cLp14zlxHsKgkM4pqMHaJhcMroS68ASvfe7dMW8yzwCgB4yJoLQ0SjWWU+MKzuFDGaJRdakQrnBbhdPbHO2qMA==";
    npmDepsHash = "sha256-4AAoUsV47eDd342i0C9VYGmtamAyZ8+0IKsvO58Vo+A=";
    lockFile = ../../pkgs/pi-chrome-devtools/package-lock.json;
    description = "Chrome DevTools Protocol tools for Pi";
  };

  pi-btw = mkNarumirunaExtension {
    pname = "pi-btw";
    version = "0.50.0";
    hash = "sha512-KIjT9eEiElhZ+qjj0IiVFRWzzCwSk8sEdYtrGAWXgSEFb5NaNcCt1YFkJzG2z5fFv2IUJKhpU7hn5y4GAOJWgQ==";
    npmDepsHash = "sha256-UZSqIZiCjV6LODpiisP05OHqBy3l349LHQfc6Ga0C78=";
    lockFile = ../../pkgs/pi-btw/package-lock.json;
    description = "Side-question command for Pi";
    forceEmptyCache = true;
  };

  pi-goal = mkNarumirunaExtension {
    pname = "pi-goal";
    version = "0.50.0";
    hash = "sha512-S7VK6k177WJO7T+HMcCHDsmAcKEdqu/bep7BbliYJdVOOlZ83kOoRxPYmwqSzbb5UM+vK/npIA0vQoP0cIIVJw==";
    npmDepsHash = "sha256-YgJ9weWA1G5y1jCMXJVj9UmBBmZNisvZmlP5soxzlCw=";
    lockFile = ../../pkgs/pi-goal/package-lock.json;
    description = "Persistent goal mode for Pi";
  };

  ponytail = prev.stdenvNoCC.mkDerivation {
    pname = "ponytail";
    version = "4.9.0";

    src = prev.fetchFromGitHub {
      owner = "DietrichGebert";
      repo = "ponytail";
      tag = "v4.9.0";
      hash = "sha256-8cYggVltBAlZ/Zj4pl1bOu7mQdZFXCmDGW4RSpvRA+w=";
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
    version = "2.0.1";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/pi-archimedes/-/pi-archimedes-${version}.tgz";
      hash = "sha512-dCXLffOLdCuwSHtdtEndfBp/q0esb/IY5vRXc1GMZxsVocw+Fv26GRN8Ke+sRO5QnjRqta2lL3ghb0Epi/n5iw==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-vnn1fuWzgCNRv+pXW32N5x+DlURl05jbAA0fTDkkWes=";
    dontNpmBuild = true;
    npmFlags = ["--legacy-peer-deps" "--omit=dev"];
    npmInstallFlags = ["--legacy-peer-deps" "--omit=dev"];
    npm_config_legacy_peer_deps = "true";

    postPatch = ''
      cp ${../../pkgs/pi-archimedes/package-lock.json} package-lock.json
    '';

    postFixup = ''
      substituteInPlace "$out/src/index.ts" \
        --replace-fail '      import("@pi-archimedes/image-paste").catch((e) => { console.error("[archimedes] image-paste load failed:", e); return null; }),' '      Promise.resolve(null), // ponytail: Pi core owns clipboard image handling.' \
        --replace-fail '      import("@pi-archimedes/subagent").catch((e) => { console.error("[archimedes] subagent load failed:", e); return null; }),' '      Promise.resolve(null), // ponytail: pi-subagents owns delegation.'
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
    version = "2.4.0";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/@juicesharp/rpiv-todo/-/rpiv-todo-${version}.tgz";
      hash = "sha512-MJOsfwkLyNk33SStM/q6wOey+tDGEvc3pc/oQ+/MlZbj3Pc8MJeJa7hVrVX1RGCp62M9xr03rWcvhvZicuSf1Q==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-oqrVTeGOrCNYevLSFL3RMzM7+PBKzDRNmLBUgepE9dE=";
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
    version = "0.26.8";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/@plannotator/pi-extension/-/pi-extension-${version}.tgz";
      hash = "sha512-KuVONOMdBaCjsqIsbtbwjE/w/+6xrLhkjRn9OE6FaYMFcC2uXodGYMAeb3jMLEJgS2RopZgAORPEDiBkKCrJCA==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-Ls11ahiE7BMj6TKJRhil4E3vc6/RM0juD+nCS07G/ew=";
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
    version = "0.46.0";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/pi-subagents/-/pi-subagents-${version}.tgz";
      hash = "sha512-hgldOVlaB05qXkQJRpp8wZCQ+TPZv4Xi+lu0Z2RYKRU3SaQmy3R9sCFM9myoqRSIgsLYKer41784BHbyh4QKIw==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-8YAJznRwUeN8DTGrIOm65L6wezLrIwOgwnrCkL/0Plk=";
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
    npmDepsHash = "sha256-bxPk4/fXTeb2Xozkk/DLsJpOLZQrRYmjNqtAJAHPPas=";
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
