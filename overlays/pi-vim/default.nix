{...}:
# pi-vim (https://github.com/lajarre/pi-vim) — modal vim for pi's TUI prompt.
# TypeScript source only; pi loads .ts via its own runtime transpiler.
final: prev: {
  pi-vim = prev.stdenvNoCC.mkDerivation {
    pname = "pi-vim";
    version = "0.14.2";

    src = prev.fetchurl {
      url = "https://registry.npmjs.org/pi-vim/-/pi-vim-0.14.2.tgz";
      hash = "sha512-CFSKJvOCNToueIMyBgsujT+gHa4sAlLOnT4VYZ6iCGKJ7M24eCVWFKKnnMt6tmP1rDE6T7k/AqBrb6LWzCzRaQ==";
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
