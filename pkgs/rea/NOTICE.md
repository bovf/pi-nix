# REA Nix distribution notices

REA-authored code is MIT-licensed; see `lib/rea/LICENSE` and the preserved
`THIRD_PARTY_NOTICES.md`, `DISCLAIMER.md`, `licenses/` and `third_party/` trees.
The `@lydell/node-pty` MIT notices include the same-release platform prebuild
family. Its Linux x64 ELF addon is patched only for immutable Nix library paths.
Frida is not distributed by this package.

`share/rea/package-lock.json` is the authoritative dependency inventory for this
Nix build. All installed npm packages and their original license files remain
under `lib/rea/node_modules/`. Upstream's preserved npm notice inventory describes
the release's original lock, not this regenerated Nix lock. In particular, fresh
transitive dependency releases retain their own license files alongside their
code; the older combined upstream inventory is not relabeled as current.
External Ghidra, JDK, Rizin and GNU binutils are separate Nix store dependencies
with their own licenses/notices; REA's MIT license does not relicense them.

Distribution changes: Node 22 is selected within upstream's engine bounds;
development dependencies, optional Frida and lifecycle installers are removed;
only `rea` is exported; setup/update/uninstall and MCP registration commands are
refused in the dispatcher. The skill includes distribution-specific safety and
availability guidance. All upstream MCP tools remain advertised; this is not a
claim that omitted external engines or active operations are available/approved.
Configuration and package updates belong to the owning Nix flakes/policy.
