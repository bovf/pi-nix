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
print("PASS: npm-latest core/tag/model pins; fresh locks; stable public release redirect with invalid targets rejected")
