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
  piPackages =
    {
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

      badwater-swarm = {
        name = "badwater-swarm";
        package = final.badwater-swarm;
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
    }
    // prev.lib.optionalAttrs prev.stdenv.hostPlatform.isLinux {
      badwater-video = {
        name = "badwater-video";
        package = final.badwater-video;
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
    version = "0.49.11";
    hash = "sha512-Vd3RlSqS+FjR+DoJMHltMP5TMc3HJTkxyfwmhPci5AdPykmKfQwK+9nehgv1tXO+3CXK1lq0SDdPcs0/u53TiQ==";
    npmDepsHash = "sha256-J00/RqOJl3FKiLyPPA+1IJxOh46YQVOvyOAj+dWhp0E=";
    lockFile = ../../pkgs/pi-lsp/package-lock.json;
    description = "Configurable language-server tools for Pi";
    forceEmptyCache = true;
  };

  pi-chrome-devtools = mkNarumirunaExtension {
    pname = "pi-chrome-devtools";
    version = "0.54.0";
    hash = "sha512-rYbwg6P5gaDRkoNWiqDGNoMuq0WwKPy/JqRyiNA3pTPOqLAiS+w1M1NxH3Jgit2bbXxrIOVx5zTcBUMWOuv8JQ==";
    npmDepsHash = "sha256-9czz/9ZYy/e5/tBE+klXzpCw9bmeC8UK+eDRY48ajBQ=";
    lockFile = ../../pkgs/pi-chrome-devtools/package-lock.json;
    description = "Chrome DevTools Protocol tools for Pi";
  };

  pi-btw = mkNarumirunaExtension {
    pname = "pi-btw";
    version = "0.63.2";
    hash = "sha512-oPWWViO3Tivbb0Lw15QGn0hLNDf4cdjHIbn/+gSndrAABMSaZcfM/pZswRtXPVc0qtTDsNNymyfpuaSYMZDyQQ==";
    npmDepsHash = "sha256-4nb9aBIWEz8K7m2Uz8sQ0Gx+JzM/RXmuM/7yrsaCLbA=";
    lockFile = ../../pkgs/pi-btw/package-lock.json;
    description = "Side-question command for Pi";
    forceEmptyCache = true;
  };

  pi-goal = mkNarumirunaExtension {
    pname = "pi-goal";
    version = "0.54.13";
    hash = "sha512-uUpEzoqVWc+eyQM096sGub1xdtdpoaWkW36MVdMT2fOuAtPsnaAgXGGDfuC8bgR8+MkbUC9cR75NB2gWFslneA==";
    npmDepsHash = "sha256-+F9eoBfnMLo6zcf4eMvJXswWWuAXOokOe1JgL71vj1c=";
    lockFile = ../../pkgs/pi-goal/package-lock.json;
    description = "Persistent goal mode for Pi";
  };

  ponytail = prev.stdenvNoCC.mkDerivation {
    pname = "ponytail";
    version = "5.3.3";

    src = prev.fetchFromGitHub {
      owner = "DietrichGebert";
      repo = "ponytail";
      tag = "v5.3.3";
      hash = "sha256-CY0EifTY0UVc6/FPGVJjEfYEf/8QLsINQmoYYKZYh98=";
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

  pi-archimedes = let
    pi = final.pi-coding-agent;
    footerCheck = let
      success = "PASS: actual packaged footer, real Git ahead=1, Pi dark/light themes, 28 renders; no prompt";
    in ''
      fixture=$(mktemp -d "$TMPDIR/archimedes-footer.XXXXXXXX")
      mkdir "$fixture/home" "$fixture/tmp"
      status=0
      (
        cd "$fixture/home"
        env -i HOME="$fixture/home" TMPDIR="$fixture/tmp" \
          PATH=${prev.lib.makeBinPath [pi.nodejs prev.git prev.bash prev.coreutils]} \
          GIT_CONFIG_NOSYSTEM=1 PI_OFFLINE=1 \
          ${prev.coreutils}/bin/timeout --kill-after=5s 60s \
          ${pi.nodejs}/bin/node ${../../tests/archimedes-footer.mjs} \
          ${pi} "$out"
      ) > "$fixture/stdout" 2> "$fixture/stderr" || status=$?
      if [ "$status" -ne 0 ] || [ -s "$fixture/stderr" ] || ! grep -Fxq '${success}' "$fixture/stdout"; then
        cat "$fixture/stdout" "$fixture/stderr" >&2
        echo "ERROR: PI_ARCHIMEDES_FOOTER_REGRESSION: refusing Archimedes and dependent generation builds." >&2
        echo "Pi ${pi.version}: ${pi}; Archimedes: $out; test exit status: $status." >&2
        echo "Check deadline: 60 seconds (timeout exits 124; forced kill exits 137)." >&2
        echo "Inspect the footer/theme/loader diagnostics above; do not bypass this compatibility check." >&2
        exit 1
      fi
      cat "$fixture/stdout"
      rm -rf "$fixture"
    '';
  in
    prev.buildNpmPackage rec {
      pname = "pi-archimedes";
      version = "2.12.0";

      src = prev.fetchurl {
        url = "https://registry.npmjs.org/pi-archimedes/-/pi-archimedes-${version}.tgz";
        hash = "sha512-PdmOK5O3ux5IpKRd8TMxEYYvHGHX2HqLgNHMOo6wzejImFeVQNMSBxo7B1Lrwr+gsAv2Tc9Y/xa1GFyLYE6eBg==";
      };

      sourceRoot = "package";
      npmDepsHash = "sha256-ANlRge7tZd1V9k5Zd7XD4bC6WJgyF8VOLB6DXtWRn74=";
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
        # Archimedes 2.10 fixes the footer color upstream; no compatibility patch.
      '';

      installPhase = ''
        runHook preInstall
        mkdir -p $out
        cp -r . $out/
        runHook postInstall
      '';

      # A passthru test alone would not block Home Manager/NixOS generation builds.
      doInstallCheck = true;
      installCheckPhase = ''
        runHook preInstallCheck
        ${footerCheck}
        runHook postInstallCheck
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
    version = "2.15.0";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/@juicesharp/rpiv-todo/-/rpiv-todo-${version}.tgz";
      hash = "sha512-8WfYssdgQgSWzFNsRzdw5Z6ZJIjO2ecM/YqEzYpR/ore+Hh5aNmafGVy94uFbIofAv2wGGitx5e3J/ucRrViXQ==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-sjdMY3ckkuP6Ch/LK+6880QslDzFSgrDaeBfANuYj6U=";
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
    version = "0.28.37";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/@plannotator/pi-extension/-/pi-extension-${version}.tgz";
      hash = "sha512-QHEP1Nzo3GHDpVJ/+2FfCIPZe0z7tjUs2ttQtmz8nB0f5j90VbZT5UmnvwqxQYJtA/qYPJ1N6aRjAABM4O7GLQ==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-LWU32GEpCySpcWqNxiEVS9z3tgo0aNsGy+c9gNOhZMw=";
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
    version = "0.84.0";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/pi-subagents/-/pi-subagents-${version}.tgz";
      hash = "sha512-IagE1hcBxLi82jTxTmcy/pIWckBuqhMH1GfAOe6/aIMVfnopMybCbcTMUS5K0CNy4tqSwHGleaXabaDmJS1QOg==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-O8R0DAEYDwtvabZvdaKWSEtNYu9cZLLeSkNUlubBZkU=";
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
    npmDepsHash = "sha256-9yQs0orrzTCc0aL6KhJ7Si5OMPcUsiYtbqaRNg7HR8A=";
    npmDepsFetcherVersion = 2;
    dontNpmBuild = true;
    npmFlags = ["--legacy-peer-deps" "--omit=dev"];
    npmInstallFlags = ["--legacy-peer-deps" "--omit=dev"];
    npm_config_legacy_peer_deps = "true";

    postPatch = ''
      ${prev.jq}/bin/jq -f ${../../pkgs/remote-pi/host-peers.jq} package.json > package.json.upstream
      ${prev.jq}/bin/jq 'del(.devDependencies)' package.json.upstream > package.json.nix
      mv package.json.nix package.json
      cp ${../../pkgs/remote-pi/package-lock.json} package-lock.json
    '';

    installPhase = ''
      runHook preInstall
      mv package.json.upstream package.json
      rm package-lock.json
      mkdir -p $out
      cp -r . $out/
      # Standalone CLI/native ESM consumers cannot use Pi's extension aliases.
      # Link the same host modules, never private npm copies of the peers.
      host=${final.pi-coding-agent}/lib/pi/node_modules
      mkdir -p $out/node_modules/@earendil-works
      ln -s "$host/@earendil-works/pi-coding-agent" $out/node_modules/@earendil-works/pi-coding-agent
      ln -s "$host/@earendil-works/pi-tui" $out/node_modules/@earendil-works/pi-tui
      ln -s "$host/typebox" $out/node_modules/typebox
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
