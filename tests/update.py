#!/usr/bin/env python3
"""Offline regression check for npm-latest core pins and fresh extension locks.

Run: python3 tests/update.py (bash and jq on PATH).
"""
import json
from pathlib import Path
import subprocess
import tempfile
import textwrap

ROOT = Path(__file__).resolve().parents[1]
updater = (ROOT / "nix/apps/update.nix").read_text()


def shell_section(start, end):
    return textwrap.dedent(updater.split(start, 1)[1].split(end, 1)[0]).replace("''${", "${")


with tempfile.TemporaryDirectory() as directory:
    tmp = Path(directory)
    overlay = tmp / "overlays/pi-coding-agent/default.nix"
    overlay.parent.mkdir(parents=True)
    overlay.write_text((ROOT / "overlays/pi-coding-agent/default.nix").read_text())
    core = "update_pi_core() {" + shell_section("        update_pi_core() {", "        update_ponytail() {")
    subprocess.run(["bash", "-euc", '''
        npm_meta() {
          case "$1" in
            '@earendil-works%2fpi-coding-agent') echo '{"dist-tags":{"latest":"9.8.7"}}' ;;
            '@earendil-works%2fpi-ai/9.8.7') echo '{"dist":{"integrity":"sha512-model"}}' ;;
            *) return 1 ;;
          esac
        }
        nix() {
          test "$*" = 'store prefetch-file --json https://github.com/earendil-works/pi/archive/refs/tags/v9.8.7.tar.gz'
          echo '{"hash":"sha256-source"}'
        }
        resolve_build_hash() { :; }
    ''' + core + "\nupdate_pi_core\n"], cwd=tmp, check=True)
    result = overlay.read_text()
    assert 'version = "9.8.7";' in result
    assert 'hash = "sha256-source";' in result
    assert 'hash = "sha512-model";' in result
    assert 'npmDepsHash = prev.lib.fakeHash;' in result

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
print("PASS: npm-latest core/tag/model pins; published locks removed before regeneration")
