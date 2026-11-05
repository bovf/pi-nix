#!/usr/bin/env python3
"""Offline regression check for upstream-owned core and fresh extension locks.

Run: python3 tests/update.py (bash and jq on PATH).
"""
import json
import os
import re
import subprocess
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
updater = (ROOT / "nix/apps/update.nix").read_text()


def shell_section(start, end):
    return textwrap.dedent(updater.split(start, 1)[1].split(end, 1)[0]).replace("''${", "${")


# Core source, catalog and dependency hashes are owned by the locked upstream flake.
flake = (ROOT / "flake.nix").read_text()
core = (ROOT / "overlays/pi-coding-agent/default.nix").read_text()

assert re.search(r'url = "github:earendil-works/pi/v[0-9]+\.[0-9]+\.[0-9]+";', flake)
assert 'update_release_input "pi-upstream" "earendil-works/pi"' in updater
assert 'update_release_input "hunk" "modem-dev/hunk"' in updater
assert 'inputs.nixpkgs.follows = "nixpkgs";' in flake.split('pi-upstream = {', 1)[1].split('};', 1)[0]
assert 'runtimeInputs = with pkgs; [curl jq nix nodejs_22 python3 git];' in updater
assert 'update_pi_core' not in updater
assert 'nix flake update' in updater
assert 'prev.callPackage "${pi-upstream}/nix/package.nix"' in core
assert 'attrs.pname == "pi-workspace-packages"' in core
assert 'prev.lib.strings.addContextFrom lock' in core
assert all(field not in core for field in ['npmDepsHash', 'modelData', 'buildNpmPackage'])
assert 'for workspace in durable chord;' in core
assert 'pack_package packages/schema schema' in core
assert '"node_modules/@earendil-works/pi-schema" = "${compiled}/schema.tgz";' in core
assert 'Upstream now supplies pi-schema; retire its local artifact bridge' in core
assert 'Upstream now packs pi-schema; retire its local artifact bridge' in core
assert 'tests/core-schema.mjs' in core
assert 'pack_package packages/chord chord' in core
assert all(f'packages/{name}' not in core for name in ['protocol', 'client', 'server'])

# Local packages still carry external dependencies: refresh axe and build every
# advertised native runtime instead of freezing additions outside the old list.
assert 'update_simple_npm "axe" "axe-core" "overlays/badwater-senior-swarm/default.nix"' in updater
for name in ['badwater-video', 'badwater-craft-mcp', 'badwater-senior-swarm', 'badwater-senior-swarm-browser', 'badwater-gitlab', 'badwater-screenshot']:
    assert f'.#{name} ' in updater
simple = 'update_simple_npm() {' + shell_section('        update_simple_npm() {', '        update_pi_package() {')
with tempfile.TemporaryDirectory() as directory:
    tmp = Path(directory)
    overlay = tmp / 'overlays/badwater-senior-swarm/default.nix'
    overlay.parent.mkdir(parents=True)
    original = (ROOT / 'overlays/badwater-senior-swarm/default.nix').read_text()
    overlay.write_text(original)
    subprocess.run(['bash', '-euc', '''
        npm_meta() { printf '%s' '{"dist-tags":{"latest":"9.9.9"},"versions":{"9.9.9":{"dist":{"integrity":"sha512-fixture","tarball":"https://registry.npmjs.org/axe-core/-/axe-core-9.9.9.tgz"}}}}'; }
    ''' + simple + '\nupdate_simple_npm axe axe-core overlays/badwater-senior-swarm/default.nix\n'], cwd=tmp, check=True)
    updated = overlay.read_text()
    assert 'version = "9.9.9";' in updated and 'axe-core-9.9.9.tgz' in updated and 'hash = "sha512-fixture";' in updated
    assert updated.count('version = "0.1.0";') == original.count('version = "0.1.0";')

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
release = "github_release() {" + shell_section("        github_release() {", "        update_release_input() {")
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
# Stable release URLs must advance before locking, without touching unrelated inputs.
release_input = "update_release_input() {" + shell_section("        update_release_input() {", "        resolve_build_hash() {")
with tempfile.TemporaryDirectory() as directory:
    tmp = Path(directory)
    flake_file = tmp / "flake.nix"
    original = 'pi-upstream.url = "github:earendil-works/pi/v1.1.0"; hunk.url = "github:modem-dev/hunk/v0.22.0"; other.url = "github:owner/other";\n'
    # Keep shell interpolation and authentication out of this offline fixture.
    for tag, succeeds in [("v1.2.0", True), ("v1.2.0-beta.1", False), ("main", False)]:
        flake_file.write_text(original)
        result = subprocess.run(["bash", "-euc", 'github_release() { printf \'{\"tag_name\":\"%s\"}\\n\' "$1"; };\n' +
            release_input.replace('release=$(github_release "$repo")', 'release=$(github_release "$TEST_TAG")') +
            '\nupdate_release_input pi-upstream earendil-works/pi\n', "test"], cwd=tmp,
            env={**os.environ, "TEST_TAG": tag}, capture_output=True, text=True, check=False)
        assert (result.returncode == 0) == succeeds, result.stderr
        assert flake_file.read_text() == (original.replace("/pi/v1.1.0", "/pi/" + tag) if succeeds else original)

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
# Upstream now handles its sole optional export; keep the retired local patch gone.
packages = (ROOT / "overlays/pi-packages/default.nix").read_text()
assert "runner-aliases.js" not in packages
assert "@earendil-works/pi-agent-core/node" not in packages
# REA is a CLI/MCP package, not a Pi extension; refresh its independently located
# recipe with the same fresh-lock/hash pipeline and the shared installer filter.
assert 'update_pi_package "rea" "rea-agents" "pkgs/rea" "$(cat pkgs/rea/package-filter.jq)" "overlays/rea/default.nix"' in updater
assert 'local source_file="\'\'${5:-overlays/pi-packages/default.nix}"' in updater
assert 'resolve_build_hash "$attr" "$source_file" "npmDepsHash"' in updater
assert '.#rea ' in updater
assert 'python3 ${./audit-rea-ghidra.py}' in updater
subprocess.run(['python3', str(ROOT / 'nix/apps/audit-rea-ghidra.py'), '--self-test'], check=True)
rea_lock = json.loads((ROOT / "pkgs/rea/package-lock.json").read_text())
rea_root = rea_lock["packages"][""]
assert rea_root["dependencies"]["@lydell/node-pty"] == "1.1.0"
assert not any(rea_root.get(field) for field in ["devDependencies", "optionalDependencies"])
assert not any(key.endswith("node_modules/frida") for key in rea_lock["packages"])
filtered = json.loads(subprocess.check_output(["jq", "-f", str(ROOT / "pkgs/rea/package-filter.jq")], input=json.dumps({"name": "fixture", "dependencies": {"kept": "^1"}, "optionalDependencies": {"frida": "1"}, "devDependencies": {"dev": "2"}, "scripts": {"install": "download"}, "allowScripts": {"frida": True}}), text=True))
assert filtered == {"name": "fixture", "dependencies": {"kept": "^1"}}
# Exercise the real shared updater against a private REA archive/recipe, with
# registry/npm/Nix boundaries mocked. This catches a recipe-location/hash seam
# regression without running a full update or touching any live installation.
rea_updater = "update_pi_package() {" + shell_section("        update_pi_package() {", '        update_release_input "pi-upstream"')
with tempfile.TemporaryDirectory() as directory:
    import tarfile
    tmp = Path(directory)
    package = tmp / "archive/package"
    package.mkdir(parents=True)
    (package / "package.json").write_text(json.dumps({"name": "rea-agents", "version": "9.0.0", "dependencies": {"kept": "^1"}, "optionalDependencies": {"frida": "1"}, "scripts": {"install": "download"}}))
    (package / "npm-shrinkwrap.json").write_text("stale")
    with tarfile.open(tmp / "archive.tgz", "w:gz") as archive:
        archive.add(package, arcname="package")
    (tmp / "overlays/rea").mkdir(parents=True)
    (tmp / "pkgs/rea").mkdir(parents=True)
    (tmp / "overlays/rea/default.nix").write_text((ROOT / "overlays/rea/default.nix").read_text())
    (tmp / "pkgs/rea/package-filter.jq").write_text((ROOT / "pkgs/rea/package-filter.jq").read_text())
    subprocess.run(["bash", "-euc", '''
        npm_meta() { printf '%s' '{"dist-tags":{"latest":"9.0.0"},"versions":{"9.0.0":{"dist":{"integrity":"sha512-fixture","tarball":"https://registry.npmjs.org/rea-agents/-/rea-agents-9.0.0.tgz"}}}}'; }
        curl() { cat archive.tgz; }
        npm() {
          test ! -e npm-shrinkwrap.json
          test ! -e package-lock.json
          test "$*" = 'install --package-lock-only --ignore-scripts --omit=dev --legacy-peer-deps --no-audit --no-fund'
          jq -e '.dependencies.kept == "^1" and .optionalDependencies == null and .scripts == null' package.json >/dev/null
          printf '%s' '{"lockfileVersion":3}' > package-lock.json
        }
        # curl runs from the fixture root before npm changes into its temp dir.
        fill_missing_integrities() { test -e "$1"; }
        resolve_build_hash() { test "$*" = 'rea overlays/rea/default.nix npmDepsHash'; }
    ''' + rea_updater + '\nupdate_pi_package rea rea-agents pkgs/rea "$(cat pkgs/rea/package-filter.jq)" overlays/rea/default.nix\n'], cwd=tmp, check=True)
    updated = (tmp / "overlays/rea/default.nix").read_text()
    assert 'version = "9.0.0";' in updated
    assert 'hash = "sha512-fixture";' in updated
    assert 'npmDepsHash = prev.lib.fakeHash;' in updated
    assert json.loads((tmp / "pkgs/rea/package-lock.json").read_text())["lockfileVersion"] == 3
print("PASS: upstream input-owned core; fresh locks; rooted builds; stable release redirect; shared remote-pi host-peer normalization and copy-free lock; retired subagents alias patch; REA updater/filter/native optional lock coverage; axe/local-runtime updater coverage")
