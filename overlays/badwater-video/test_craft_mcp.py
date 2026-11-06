"""Accept only complete healthy LightCraft load reports, not warnings or repairs."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from craft_mcp import light_report_pattern, scoped_command

assert len(sys.argv) == 2, 'Provide the actual managed Craft defaults JSON'
DEFAULTS = json.loads(Path(sys.argv.pop()).read_text())


class LightReport(unittest.TestCase):
    def setUp(self):
        self.root = Path('/private/native/lightcraft')
        self.pattern = light_report_pattern(self.root)
        self.old = f'lightcraft-cli mcp: opened library {self.root / "library"} (LoadReport {{ snapshot_seq: 0, replayed: 0, stale: 0, failed: 0, torn_bytes: 0, torn_fragments: 0, damaged: None, created: true, upgraded_from: None }})\n'
        self.current = self.old.replace('upgraded_from: None', 'upgraded_from: None, repaired: []')

    def test_old_and_current_healthy_shapes(self):
        for line in [self.old, self.current, self.current.replace('created: true', 'created: false').replace('snapshot_seq: 0', 'snapshot_seq: 42')]:
            with self.subTest(line=line): self.assertIsNotNone(self.pattern.fullmatch(line))

    def test_damage_repair_unknown_and_wrong_root_stay_diagnostic(self):
        mutations = [
            ('stale: 0', 'stale: 1'), ('failed: 0', 'failed: 1'),
            ('torn_bytes: 0', 'torn_bytes: 1'), ('torn_fragments: 0', 'torn_fragments: 1'),
            ('damaged: None', 'damaged: Some(error)'), ('upgraded_from: None', 'upgraded_from: Some(1)'),
            ('repaired: []', 'repaired: [repair]'), ('repaired: []', 'repaired: [], unknown: 0'),
            (str(self.root), '/other/native/lightcraft'),
        ]
        for old, new in mutations:
            with self.subTest(new=new): self.assertIsNone(self.pattern.fullmatch(self.current.replace(old, new)))
        for line in [self.current.rstrip(), self.current + 'warning\n', 'warning: ' + self.current]:
            self.assertIsNone(self.pattern.fullmatch(line))


class Namespace(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='craft-scope-')
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        self.raw = base / 'raw'; self.raw.mkdir()
        self.derived = base / 'derived'; self.derived.mkdir()
        self.root = self.derived / 'photocraft'; self.root.mkdir()
        (self.raw / 'immutable').write_text('raw')
        (self.derived / 'sibling').write_text('private sibling')
        self.config = {**DEFAULTS, 'readRoots': [str(self.raw)], 'writeRoot': str(self.derived)}

    def test_readable_memory_without_expanding_filesystem_or_child_privileges(self):
        probe = '''import os
from pathlib import Path
status = Path('/proc/self/status').read_text()
for key in ['CapEff:', 'CapBnd:', 'CapAmb:']:
 assert next(line.split()[1] for line in status.splitlines() if line.startswith(key)) == '0000000000000000'
assert 'NoNewPrivs:\\t1' in status
mounts = [line.split() for line in Path('/proc/self/mountinfo').read_text().splitlines()]
assert any(line[4] == '/sys/fs/cgroup' and 'ro' in line[5].split(',') and 'cgroup2' in line for line in mounts)
assert any(line[4] == '/' and 'ro' in line[5].split(',') for line in mounts)
assert Path('/sys/fs/cgroup/cgroup.controllers').is_file()
root = Path(os.environ['HOME']).parent
assert not (root.parent / 'sibling').exists()
Path(root / 'allowed').write_text('allowed')
'''
        probe += f'''\nraw = Path({str(self.raw / 'immutable')!r})
assert raw.read_text() == 'raw'
try:
 raw.write_text('forbidden')
 raise AssertionError('raw write succeeded')
except OSError as exc:
 assert exc.errno == 30
'''
        result = subprocess.run(scoped_command(self.config, 'photocraft', [sys.executable, '-c', probe], self.root), capture_output=True, text=True, timeout=20, check=False)
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        self.assertEqual((self.root / 'allowed').read_text(), 'allowed')
        self.assertEqual((self.derived / 'sibling').read_text(), 'private sibling')

    def test_mount_failure_is_closed_and_other_apps_keep_original_namespace(self):
        argv = [sys.executable, '-c', 'raise AssertionError("editor must not start after mount failure")']
        result = subprocess.run(scoped_command({**self.config, 'mount': '/missing-mount'}, 'photocraft', argv, self.root), capture_output=True, text=True, timeout=20, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('/missing-mount', result.stderr)
        self.assertNotIn('AssertionError', result.stderr)
        other = scoped_command(self.config, 'filmcraft', argv, self.root)
        self.assertNotIn('--cap-add', other)
        self.assertEqual(other[-len(argv):], argv)


if __name__ == '__main__':
    unittest.main()
