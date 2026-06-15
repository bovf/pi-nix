{...}:
# pi-vim (https://github.com/lajarre/pi-vim) — modal vim for pi's TUI prompt.
# TypeScript source only; pi loads .ts via its own runtime transpiler.
final: prev: {
  pi-vim = prev.stdenvNoCC.mkDerivation {
    pname = "pi-vim";
    version = "0.12.1";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/pi-vim/-/pi-vim-0.12.1.tgz";
      hash = "sha512-zAPAS8+pMaM/gjqXZ1PAI3B+N/Q8Q3gWXX+TlUmu9bmBkmuN5XWXdq+6YAGD+W0aHR92HUnrM6o6oD+p8pSO5g==";
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
