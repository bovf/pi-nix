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
    version = "0.49.5";
    hash = "sha512-okjzWwcN6LvvvPwfcHEAiuBJPSii/DbYfD6YCSVdXpx/okG1erIUMx9mJiC/oM1NVgOQctaB42sNQ+PNYvLPrw==";
    npmDepsHash = "sha256-gPLX155AK6fvJCQ6KZ+DrpLXjlv4bPi6Izq1UiGqEys=";
    lockFile = ../../pkgs/pi-lsp/package-lock.json;
    description = "Configurable language-server tools for Pi";
    forceEmptyCache = true;
  };

  pi-chrome-devtools = mkNarumirunaExtension {
    pname = "pi-chrome-devtools";
    version = "0.52.1";
    hash = "sha512-93QpXiodfY1e330qa8IY+Yyxw2OmVT6A/7EPpGZAbNzymzRL/B5lS8zc8Zv92PnOERrjj4aJOIn0FPGZINE3Uw==";
    npmDepsHash = "sha256-TNmtDCbAF68sUsccOVxiyc1OmGWDjSucG3CLA9neHik=";
    lockFile = ../../pkgs/pi-chrome-devtools/package-lock.json;
    description = "Chrome DevTools Protocol tools for Pi";
  };

  pi-btw = mkNarumirunaExtension {
    pname = "pi-btw";
    version = "0.55.1";
    hash = "sha512-7xIr1f+q2uhvxTbEVzLKzbwt7x6NOPCWM8OQWo8GceqCOruGwjMLfNmznEbobXWAXQBn1IlTVVhewSDFYmiOYw==";
    npmDepsHash = "sha256-sqc05puMKHNPZvpPrClyBg9G9jynetQvVGRKoWLqdeA=";
    lockFile = ../../pkgs/pi-btw/package-lock.json;
    description = "Side-question command for Pi";
    forceEmptyCache = true;
  };

  pi-goal = mkNarumirunaExtension {
    pname = "pi-goal";
    version = "0.53.0";
    hash = "sha512-cmWowqAzlkgRLKYp2hFnUZvEEs6G6aGjEOazBWNW88T7LB9cd/AzOFOGYvA1QxxsGtIdOuFRZJVhfAJDGsAcjw==";
    npmDepsHash = "sha256-B4nwrp8q9We5Rv+Rgi///SVDjEHCkZ3nQq/UnbJG9sw=";
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
    version = "2.2.0";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/pi-archimedes/-/pi-archimedes-${version}.tgz";
      hash = "sha512-gLBSCipwDaYZestNmDihrq2blNevdm09D74qfruSygsKqsnH8KjUoUDUbGEm4Cr2pJxZlFus22BuGkCWFzHryg==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-fVpy6FHzz0OncR9QfBy9nDRxhGUo4kaoAoE5J1OcNlE=";
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
    version = "2.7.0";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/@juicesharp/rpiv-todo/-/rpiv-todo-${version}.tgz";
      hash = "sha512-3jy8WIUY2q2TYLMPUwuSTugBHwlkDLccAqRymU700vZKXeJZNxg99B+pcT2ochIF31QsReNY8zpDKG+kxh5yNQ==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-dq1mnyhBgfFTt1Z/sVfgq+3O1Pih4avumAZ5kNsYhzg=";
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
    version = "0.27.6";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/@plannotator/pi-extension/-/pi-extension-${version}.tgz";
      hash = "sha512-1VfGGe0hIBOyCe1+TdXU9EH4OrLCtw4fagw7P2QpJ1JgKldNnhPxyix+aAIjIqA3b9W9EQu/S4dL/YYhjmLcEg==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-jMpQI7tMokPMFeEWT+DLj0ogGQ4d6hom9zpBjvKgF1M=";
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
    version = "0.55.0";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/pi-subagents/-/pi-subagents-${version}.tgz";
      hash = "sha512-YRjaDcFWNZrDG7mYSSy4LQn/uXo0VDEpVDyXsXjHgSU0FAHp9fnuLtAjm6y1g7BxFf1Lp3RB1O//325PD5bplg==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-6lIHd/IrH4PeehNJF1OSqdVodHcetRAUc3UE0sLmDpc=";
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
    npmDepsHash = "sha256-JH/f+pJH/ZwzEcMSuDeRBwaQqREAG8cI5yucez5gT78=";
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
