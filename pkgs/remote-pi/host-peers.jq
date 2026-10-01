# Native remote-pi CLI imports need these peers too; Nix links the matching host.
del(.dependencies["@earendil-works/pi-coding-agent"],
    .dependencies["@earendil-works/pi-tui"], .dependencies.typebox)
| .peerDependencies += {
    "@earendil-works/pi-coding-agent": "*",
    "@earendil-works/pi-tui": "*",
    "typebox": "*"
  }
