"""Audit the operator-pinned REA-compatible Ghidra archive; never relax REA's guard."""
import base64
import json
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any


def validate(pin, release):
    if release['tag_name'] != pin['tag'] or release['draft'] or release['prerelease']:
        raise ValueError('Ghidra pin is not the approved stable release')
    if pin['tag'] != f"Ghidra_{pin['version']}_build":
        raise ValueError('Ghidra version/tag mismatch')
    name = f"ghidra_{pin['version']}_PUBLIC_{pin['versionDate']}.zip"
    url = f"https://github.com/NationalSecurityAgency/ghidra/releases/download/{pin['tag']}/{name}"
    assets = [a for a in release['assets'] if a['name'] == name and a['browser_download_url'] == url]
    if pin['url'] != url or len(assets) != 1:
        raise ValueError('Ghidra archive is not the exact approved release asset')
    digest = assets[0].get('digest', '')
    if not digest.startswith('sha256:'):
        raise ValueError('Ghidra release asset has no authoritative SHA256 digest')
    expected = 'sha256-' + base64.b64encode(bytes.fromhex(digest.removeprefix('sha256:'))).decode()
    if pin['hash'] != expected:
        raise ValueError('Ghidra release digest differs from the approved pin')


def main():
    pin = json.loads(Path('overlays/rea/ghidra.json').read_text())
    request = urllib.request.Request(f"https://api.github.com/repos/NationalSecurityAgency/ghidra/releases/tags/{pin['tag']}", headers={'User-Agent': 'pi-nix-update'})
    with urllib.request.urlopen(request, timeout=45) as response:
        validate(pin, json.load(response))
    subprocess.run(['nix', 'store', 'prefetch-file', '--json', '--expected-hash', pin['hash'], pin['url']], check=True)
    print(f"REA Ghidra: audited intentional compatible pin {pin['version']}; no global nixpkgs override")


if __name__ == '__main__':
    if sys.argv[1:] == ['--self-test']:
        import copy
        pin = {'version': '12.1.4', 'versionDate': '20260921', 'tag': 'Ghidra_12.1.4_build', 'hash': 'sha256-' + base64.b64encode(bytes(32)).decode()}
        pin['url'] = f"https://github.com/NationalSecurityAgency/ghidra/releases/download/{pin['tag']}/ghidra_{pin['version']}_PUBLIC_{pin['versionDate']}.zip"
        release: dict[str, Any] = {'tag_name': pin['tag'], 'draft': False, 'prerelease': False, 'assets': [{'name': 'ghidra_12.1.4_PUBLIC_20260921.zip', 'browser_download_url': pin['url'], 'digest': 'sha256:' + '00' * 32}]}
        validate(pin, release)
        for change in ['tag', 'prerelease', 'url', 'digest']:
            bad = copy.deepcopy(release)
            if change == 'tag': bad['tag_name'] = 'Ghidra_12.2_build'
            elif change == 'prerelease': bad['prerelease'] = True
            else: bad['assets'][0]['browser_download_url' if change == 'url' else 'digest'] = 'unexpected'
            try: validate(pin, bad)
            except ValueError: pass
            else: raise AssertionError('accepted invalid ' + change)
        print('PASS exact stable Ghidra tag/asset/digest checks and negative controls')
    elif not sys.argv[1:]:
        main()
    else:
        raise SystemExit('Usage: audit-rea-ghidra.py [--self-test]')
