{...}:
# pi-vim (https://github.com/lajarre/pi-vim) — modal vim for pi's TUI prompt.
# TypeScript source only; pi loads .ts via its own runtime transpiler.
final: prev: {
  pi-vim = prev.stdenvNoCC.mkDerivation {
    pname = "pi-vim";
    version = "0.11.0";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/pi-vim/-/pi-vim-0.11.0.tgz";
      hash = "sha256-/wgW4tBtEAEvIZ0O8PPlIpXg2Vhm0JJYzz0+iFRdIjk=";
    };

    sourceRoot = "package";
    dontConfigure = true;
    dontBuild = true;

    installPhase = ''
      runHook preInstall
      mkdir -p $out
      cp -r . $out/
      runHook postInstall
    '';

    meta = {
      description = "Vim-style modal editing for pi's TUI editor";
      homepage = "https://github.com/lajarre/pi-vim";
      license = prev.lib.licenses.mit;
      platforms = prev.lib.platforms.unix;
    };
  };
}
