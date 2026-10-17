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
    version = "0.49.10";
    hash = "sha512-YgSCMh4YKlDofFA5dKcsLmXGeJs6kUkcAUewhErNpMt3JhaTJ0O563xdLQynBiqz6l9bcIlWOUIJG1RMKQUzDA==";
    npmDepsHash = "sha256-4MkpblMO5Zb9xOIGYjUvLngkfJhkb4lHSNgZH71YOWE=";
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
    version = "0.61.2";
    hash = "sha512-XPjT5fidNltCy971jBr2NoJCnJCN5AfGRVi/4qKl6V1oa+SXh1hr4rZzp3p+BLTxTqmllKNyL20TV4E6SFHTjA==";
    npmDepsHash = "sha256-cTOL4GcP0dGgHCkh/hG6ltlTtLSBqPaaRH/sL7BIxTA=";
    lockFile = ../../pkgs/pi-btw/package-lock.json;
    description = "Side-question command for Pi";
    forceEmptyCache = true;
  };

  pi-goal = mkNarumirunaExtension {
    pname = "pi-goal";
    version = "0.54.12";
    hash = "sha512-23t+dM32yLdSQh3SdzKg9ExS3iaUFhgre26vxcc6Jq9ZxV/kjuPK70wa/y5uJcrB84nWqRXoEcwvKwFbcvUPKQ==";
    npmDepsHash = "sha256-aaPg4pL0/cOWeMTc57rRre4+4uXe2V/jq8es8c9ZYnI=";
    lockFile = ../../pkgs/pi-goal/package-lock.json;
    description = "Persistent goal mode for Pi";
  };

  ponytail = prev.stdenvNoCC.mkDerivation {
    pname = "ponytail";
    version = "5.3.2";

    src = prev.fetchFromGitHub {
      owner = "DietrichGebert";
      repo = "ponytail";
      tag = "v5.3.2";
      hash = "sha256-IJlhfkdXI6pMZZCZO7XBRg88LBiNfzc5Gnm4ofGybL8=";
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
      version = "2.11.1";

      src = prev.fetchurl {
        url = "https://registry.npmjs.org/pi-archimedes/-/pi-archimedes-${version}.tgz";
        hash = "sha512-mtG8nkfEPDusDJgHuf72bT1CePc4TzPQchT9DCEIpbIiYQRqLE5lYMQPwYn3jq5L7OZUPQS4UzRmeYJoxYl+NQ==";
      };

      sourceRoot = "package";
      npmDepsHash = "sha256-AW80qm0RqWn6od8TqbusLqcc4u9eX/XTI39cwFkRieQ=";
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
    version = "2.13.9";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/@juicesharp/rpiv-todo/-/rpiv-todo-${version}.tgz";
      hash = "sha512-fXuUVU2HlxiUMeDeRTXbSVDPftP+CMGe47nAA5H0BX4YYl7chl1M2fSL1fFQqq5FCcpk5+ZBiQ43tiKvUu97gQ==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-rCBW4VAY9xtqS2G2lNw3jVGV1FZEtg7StOn3Bm0ru0E=";
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
    version = "0.28.23";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/@plannotator/pi-extension/-/pi-extension-${version}.tgz";
      hash = "sha512-C59ZYaiv99U5cNCoISiHZdDgjEc8ZQ5ow1GCd40dymKFwmuw6ZX0QK4kfdP5qUVp9pRlCFLYrr7a0QNmIlyW9g==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-BNad3BcCLR/nWkXD5Lt45JurkErpbhqBG1WIGf2GDhA=";
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
    version = "0.79.0";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/pi-subagents/-/pi-subagents-${version}.tgz";
      hash = "sha512-9FVPNxqYEKvimSGmQF3BqdofGTrrbY33DAS9rgtlnuvdGOvhjbhZeL2bwKYi1VOaSJcV033UpcVGLbNL4H4OOA==";
    };

    sourceRoot = "package";
    npmDepsHash = "sha256-UagJu++BEIDotuh8uadR4KXwevQn0PxPAdfySVCxEP4=";
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
    npmDepsHash = "sha256-Wpn73zLp1j+3XWP0/fqA2uCMhWnc8IjRvJOGaft4q5k=";
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
