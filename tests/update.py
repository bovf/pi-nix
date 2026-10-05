#!/usr/bin/env python3
"""Offline regression check for upstream-owned core and fresh extension locks.

Run: python3 tests/update.py (bash, jq and nix on PATH).
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap

ROOT = Path(__file__).resolve().parents[1]
updater = (ROOT / "nix/apps/update.nix").read_text()


def shell_section(start, end):
    return textwrap.dedent(updater.split(start, 1)[1].split(end, 1)[0]).replace("''${", "${")


# Core source, catalog and dependency hashes are owned by the locked upstream flake.
flake = (ROOT / "flake.nix").read_text()
core = (ROOT / "overlays/pi-coding-agent/default.nix").read_text()
assert 'url = "github:earendil-works/pi/stable";' in flake
assert 'inputs.nixpkgs.follows = "nixpkgs";' in flake.split('pi-upstream = {', 1)[1].split('};', 1)[0]
assert 'update_pi_core' not in updater
assert 'nix flake update' in updater
assert 'prev.callPackage "${pi-upstream}/nix/package.nix"' in core
assert 'attrs.pname == "pi-workspace-packages"' in core
assert 'prev.lib.strings.addContextFrom lock' in core
assert all(field not in core for field in ['npmDepsHash', 'modelData', 'buildNpmPackage'])
assert 'for workspace in durable protocol client server;' in core

with tempfile.TemporaryDirectory() as directory:
    tmp = Path(directory)
    package = tmp / "package"
    package.mkdir()
    (package / "package.json").write_text(json.dumps({"name": "fixture", "version": "1.0.0"}))
    for lock in ("package-lock.json", "npm-shrinkwrap.json"):
        (package / lock).write_text("stale published lock")
    refresh = "rm -f " + shell_section('          rm -f', '          fill_missing_integrities "$tmp/package/package-lock.json"')
    subprocess.run(["bash", "-euc", '''
        tmp="$1"
        npm() {
          test ! -e package-lock.json
          test ! -e npm-shrinkwrap.json
          test "$*" = 'install --package-lock-only --ignore-scripts --omit=dev --legacy-peer-deps --no-audit --no-fund'
          echo '{"lockfileVersion":3}' > package-lock.json
        }
    ''' + refresh, "test", str(tmp)], check=True)
    assert json.loads((package / "package-lock.json").read_text())["lockfileVersion"] == 3

    rooted_build = "resolve_build_hash() {" + shell_section(
        "        resolve_build_hash() {", "        update_ponytail() {")
    subprocess.run(["bash", "-euc", '''
        build_roots="$1"
        nix() { test "$*" = "build .#fixture --out-link $build_roots/fixture"; }
    ''' + rooted_build + '\nresolve_build_hash fixture unused unused\n',
        "test", str(tmp)], check=True)
release = "github_release() {" + shell_section("        github_release() {", "        resolve_build_hash() {")
subprocess.run(["bash", "-euc", '''
    unset GITHUB_TOKEN GH_TOKEN
    curl() {
      case "$*" in
        '-fsSL https://api.github.com/repos/owner/repo/releases/latest') return 22 ;;
        '-fsSL -o /dev/null -w %{url_effective} https://github.com/owner/repo/releases/latest')
          printf '%s' "$mock_release_url" ;;
        *) return 1 ;;
      esac
    }
''' + release + '''
    mock_release_url=https://github.com/owner/repo/releases/tag/v4.10.0
    test "$(github_release owner/repo | jq -r .tag_name)" = v4.10.0
    for mock_release_url in https://github.com/owner/repo/releases/latest \\
        https://github.com/other/repo/releases/tag/v4.10.0 \\
        https://github.com/owner/repo/releases/tag/v4.10.0-beta.1; do
      if github_release owner/repo >/dev/null 2>&1; then
        echo 'accepted an invalid release redirect' >&2
        exit 1
      fi
    done
'''], check=True)
# The updater and installed package share this exact normalization. Preserve all
# unrelated constraints and metadata, including standalone binaries.
peers = ["@earendil-works/pi-coding-agent", "@earendil-works/pi-tui", "typebox"]
manifest = {"dependencies": {**dict.fromkeys(peers, "^0.1.0"), "ws": "^8.21.0"},
            "peerDependencies": {"other": "^2"}, "bin": {"remote-pi": "dist/index.js"}}
normalized = json.loads(subprocess.check_output(
    ["jq", "-f", str(ROOT / "pkgs/remote-pi/host-peers.jq")],
    input=json.dumps(manifest), text=True))
assert normalized == {**manifest, "dependencies": {"ws": "^8.21.0"},
                      "peerDependencies": {"other": "^2", **dict.fromkeys(peers, "*")}}
assert '$(cat pkgs/remote-pi/host-peers.jq) | del(.devDependencies)' in updater
lock = json.loads((ROOT / "pkgs/remote-pi/package-lock.json").read_text())
assert all(lock["packages"][""]["peerDependencies"][peer] == "*" for peer in peers)
assert not any(key.endswith("node_modules/" + peer)
               for key in lock["packages"] for peer in peers)
# Evaluate the owning Nix patch with old/new host versions, without builds or inputs.
obsolete_alias = '@earendil-works/pi-agent-core/node'
for host_version, patched in [('0.99.2', False), ('1.0.0', True), ('1.0.2', True)]:
    expression = f'''let
      overlay = import {ROOT / 'overlays/pi-packages'} {{ hunk = {{}}; }};
      packages = overlay {{ pi-coding-agent.version = "{host_version}"; }} {{
        buildNpmPackage = x: x;
        lib.optionalString = condition: text: if condition then text else "";
        lib.versionAtLeast = a: b: builtins.compareVersions a b >= 0;
      }};
    in packages.pi-subagents.postPatch'''
    patch = subprocess.check_output(['nix', 'eval', '--offline', '--impure', '--raw', '--expr', expression], text=True,
        env={**os.environ, 'NIX_CONFIG': os.environ.get('NIX_CONFIG', '') + '\nmax-jobs = 2\ncores = 4'})
    assert (obsolete_alias in patch) == patched, (host_version, patch)
    if patched:
        assert '--replace-fail' in patch
print("PASS: upstream input-owned core; fresh locks; rooted builds; stable release redirect; shared remote-pi host-peer normalization and copy-free lock; exact subagents alias patch only on Pi >=1.0")
