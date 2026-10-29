# REA package and bounded native/static backend contract

## Stable authority and package sources

REA is [morluto/rea](https://github.com/morluto/rea), npm **rea-agents 6.8.0**.
On 2026-10-29, npm's authoritative `latest` metadata and GitHub's latest stable
release agreed: tag `rea-agents-6.8.0`, release commit
`160d821ac9a0310afcb8d1fc427862dd6508add5` (published 2026-10-25).
The compiled npm archive is the build source, not repository main or an
unverified similarly named project:

- URL: `https://registry.npmjs.org/rea-agents/-/rea-agents-6.8.0.tgz`
- SHA512: `9QDeRnGqEDzABZyr04eLnBXBv/c6I9/TWu/6M0MD4pEfkySI/BIgwTODIbAReX3C1x6hjw9+Jlx4A2yUSPZ9ww==`
- Nix dependency cache: `sha256-I77F7iVdOfJabNXtQQLLOerp1jw5Qag6922AKD/CoSo=`
- Managed lock: `pkgs/rea/package-lock.json`; normalization shared with updater:
  `pkgs/rea/package-filter.jq`.

Main's package metadata is not stable release authority: for example it declares
Playwright1.64.1/Zod4.6.6 while this release declares1.58.2/4.4.3. Dependency
constraints come from the release manifest. The fresh managed lock retains
154 dependency entries, including optional PTY platform packages, and excludes
optional Frida and development dependencies. All lifecycle scripts are disabled;
no Frida/browser/native-addon downloader is invoked. The real
`@lydell/node-pty-linux-x64@1.1.0` archive has integrity
`sha512-NcNqRTD14QT+vXcEuqSSvmWY+0+WUBn2uRE8EN0zKtDpIEr9d+YiFj16Uqds6QfcLCHfZmC+Ls7YzwTaqDnanA==`.
AutoPatchelf binds its ELF dependencies to Nix libstdc++/libgcc. Importing the
installed package loads that addon without attaching to or spawning a target.

Node must satisfy `^22.23.4 || ^24.22.1 || >=26.12.1`. The recipe explicitly
selects nixpkgs Node22 (currently22.23.4). Node24.21.0 is not acceptable. The
installed test checks the actual process version against the manifest's bound.

## Export and runtime discovery

Only `packages.x86_64-linux.rea` / `overlays.rea` is advertised for this complete
bundle. Executable: `bin/rea`. Stdio MCP command: `${rea}/bin/rea`, args
`["mcp"]`, derived from the published `scripts/rea.mjs` dispatcher. No HTTP
server is selected. Skill plus references:
`share/rea/skills/reverse-engineer-anything`; passthru exposes
`skillRelativePath`, `mcpArgs`, `runtimeBackends`, and `nodejs`.

| Bundled/discovered backend | Locked nixpkgs version | Purpose |
| --- | --- | --- |
| Ghidra | 12.1.4 | Deep native static analysis, matches REA's verified12.1.4 bridge |
| OpenJDK | 21.0.12.1+1 | Full JDK for Ghidra bridge/Java probes |
| Rizin | 0.9.1 | Explicit one-shot native static commands |
| GNU binutils | 2.46 | objdump static inspection |
| procps | 4.0.7 | Required owned-process identity checks |
| util-linux | 2.42.4 | Resource/ownership helpers; no privileges granted |

The wrapper prefixes these tool paths (plus Bash), and sets defaults for
`GHIDRA_INSTALL_DIR`, `JAVA_HOME`, and `REA_ANALYSIS_PROVIDER=ghidra`. Explicit
caller environment selections remain possible; unapproved overrides are not a
validated backend configuration. Ghidra's source and all other backend hashes
belong to the already locked nixpkgs input, not independently floating fetches.
The selected Ghidra package has only `os/linux_x86_64` native decompiler files;
ARM Linux and Darwin support for a CLI subset does not establish support for
this complete bundle. No emulation or alternate binary substitution is added.

Built-in static JavaScript/Electron, .NET and artifact-format parsers need no
proprietary engine. Optional Frida, Android engines/devices/resources, firmware
extraction engines, browser, packet/signal capture backends, and
pwntools/pwndbg/GDB are intentionally **not** installed. Hopper, IDA, Kuna, JEB
and their installers/licenses are not acquired. All229 tool definitions and six
prompts remain advertised, including tools needing those unavailable backends;
use actual tool availability/errors, not catalog size, to judge support.

## Immutable store, safety and policy boundary

The dispatcher refuses setup/update/uninstall, update-check and MCP add/remove
registration helpers, including normalized global-output flag forms and Incur's
optional leading CLI-name token (`rea rea mcp add --agent amp`). Registration
refusal is checked against both empty and existing private fixture configurations:
files, modes and timestamps must remain unchanged, not merely a nonzero exit.
Its install script is not installed. The skill carries a prominent distribution
note overriding upstream package-runner/setup advice. Package/registration/skill
ownership is declarative Nix/Home Manager policy, never a global npm installer.
The wrapper sets `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`; no browser is supplied.

REA's Ghidra launcher creates private session project, HOME, temp, XDG cache/
config/data roots, JVM `user.home`/`java.io.tmpdir` and optional extension
snapshots. The compiled bridge reads immutable shipped Java sources; writable
compilation/session state stays outside the store. No store-copy-on-start or
runtime installation patch is needed. Static provider acceptance also runs with
the entire store read-only to prove this for the exercised fixture.

This package does **not** sandbox REA in normal use. Rizin commands, debuggers,
PTY/process tools and other active surfaces have the caller's privileges.
No service, ptrace/sysctl relaxation, capture group, udev rule, credentials,
agent registration or automatic activation is installed. Supplying a backend
is not permission to execute or attach targets, capture traffic, read a browser,
use devices or inspect credentials. Separate explicit task approval is needed.
The consumer owns Heavy/Spy opt-ins; reusable policy must stay default-off and
reject unsupported-platform opt-ins without forcing this package when disabled.

## Validation and update workflow

`nix build .#checks.x86_64-linux.rea --no-link` is the package itself, with
mandatory installed checks. `tests/rea.mjs` checks startup/help/version, exact
Node bound, Ghidra-scoped read-only health, refused mutation/installer commands,
real native PTY import and absent Frida, actual stdio initialize/list229 exact
definitions/schemas and six prompts, read-only settings, and synthetic JS
inspection. Expected JS progress events are not MCP stderr; MCP must exit0 with
zero stderr. `tests/rea-native.mjs` assembles/links a tiny synthetic ELF without
executing it, and checks Ghidra overview, Rizin and GNU objdump output plus
unchanged SHA256. Use only Nix's build sandbox or an empty filesystem/network
namespace with fixture HOME; never live settings/auth or host sockets/devices.

`nix run .#update` refreshes REA's stable npm parent, fresh dependency lock,
source integrity and Nix dependency hash through the existing shared updater,
and realizes the package along with existing exports. Full update requires
x86_64-linux and refuses other hosts before pin mutation rather than silently
freezing the unsupported bundle. Existing Pi platform exports are unchanged.
`python3 tests/update.py` covers the shared normalization and updater wiring;
`python3 tests/rea-audit.py` explicitly audits current parent/dist-tag, engine/
root constraints and all dependency tarball URL/integrity tuples online. Keep
its JSON receipt outside source. Audits make no target/provider requests.

## Licenses and limits

REA-authored code is MIT. The output retains upstream LICENSE, DISCLAIMER,
THIRD_PARTY_NOTICES, `licenses/`, `third_party/`, every installed dependency's
license files and a Nix distribution notice at `share/rea/NOTICE.md`. The output
also includes the exact managed lock. Upstream's combined npm notice inventory
remains labeled as the original release inventory; freshly resolved transitive
versions retain their own notices beside their installed code. It is not
relabeled as a current Nix inventory. Frida's optional license texts may remain
in upstream's unmodified notice tree, but its code/binding is not installed.
The native PTY and external tool notices/licenses remain applicable. REA's MIT
license grants no proprietary engine entitlement and does not relicense tools.

Current bounded acceptance is x86_64 Linux synthetic/static only. It is not
live-process, network/browser, capture/device, credentials, proprietary-engine,
all-format, all229-tool, interactive or non-native-platform acceptance. Global
doctor may correctly report unhealthy because optional engines/client
registrations are absent; the selected Ghidra scope is checked independently.
