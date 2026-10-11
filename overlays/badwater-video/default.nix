{}: final: prev:
prev.lib.optionalAttrs prev.stdenv.hostPlatform.isLinux {
  badwater-video = prev.callPackage ./package.nix {};
  badwater-craft-mcp = prev.callPackage ./craft-package.nix {};
}
