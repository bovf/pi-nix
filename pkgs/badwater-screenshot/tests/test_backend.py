import os
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

from PIL import Image, PngImagePlugin

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend import CaptureEngine, rectangle

OLD = '{11111111-1111-1111-1111-111111111111}'
TARGET = '{22222222-2222-2222-2222-222222222222}'
OTHER = '{33333333-3333-3333-3333-333333333333}'


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='badwater-screenshot-test-'); self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.engine = CaptureEngine({name: '/managed/' + name for name in ['niri', 'grim', 'kdotool', 'spectacle', 'browser']}, self.base, command_runner=self.command)
        self.calls = []; self.active = OLD; self.desktop = '2'; self.fail_capture = False; self.interfere = False; self.interfere_desktop = False; self.html = ''

    def png(self, path):
        path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        meta = PngImagePlugin.PngInfo(); meta.add_text('private-fixture', 'must-not-be-forwarded')
        Image.new('RGB', (80, 50), 'navy').save(path, pnginfo=meta)

    def command(self, argv, timeout=15):
        self.calls.append(argv)
        program = Path(argv[0]).name
        if program == 'kdotool':
            if argv[1] == 'getactivewindow': return self.active
            if argv[1] == 'get_desktop': return self.desktop
            if argv[1] == 'windowactivate':
                self.active = argv[2]
                if argv[2] == TARGET: self.desktop = '9'
                return ''
            if argv[1] == 'set_desktop': self.desktop = argv[2]; return ''
            raise AssertionError(argv)
        if program == 'spectacle':
            if self.fail_capture: raise RuntimeError('synthetic capture failure')
            self.png(argv[argv.index('--output') + 1])
            if self.interfere: self.active = OTHER
            if self.interfere_desktop: self.desktop = '5'
            return ''
        if program == 'niri': self.png(argv[argv.index('--path') + 1]); return ''
        if program == 'grim': self.png(argv[-1]); return ''
        if program == 'browser':
            url = argv[argv.index('--url') + 1]
            if url.startswith('http://127.0.0.1:'): self.html = urllib.request.urlopen(url, timeout=2).read().decode()
            out = Path(argv[argv.index('--output') + 1]); out.mkdir()
            for name in ['desktop', 'mobile']: self.png(out / (name + '.png'))
            (out / 'report.json').write_text('{}')
            return ''
        raise AssertionError(argv)

    def test_capabilities_are_passive(self):
        self.assertFalse(self.engine.capabilities()['startup_capture']); self.assertEqual(self.calls, []); self.assertFalse(self.engine.root.exists())

    def test_niri_window_requires_clipboard_consent_without_focus(self):
        with self.assertRaisesRegex(ValueError, 'clipboard'): self.engine.capture('window', backend='niri', window_id='12')
        self.assertEqual(self.calls, [])
        result = self.engine.capture('window', backend='niri', window_id='12', allow_clipboard_change=True)
        self.assertEqual(result['detail']['focus'], 'unchanged'); self.assertIn('permission', result['detail']['clipboard']); self.assertFalse(any('focus-window' in call for call in self.calls))

    def test_niri_output_region_are_explicit_and_do_not_change_clipboard(self):
        with self.assertRaisesRegex(ValueError, 'output'): self.engine.capture('screen', backend='niri')
        result = self.engine.capture('screen', backend='niri', output='DP-1'); self.assertEqual(result['detail']['clipboard'], 'unchanged')
        self.assertIn('-o', self.calls[-1]); self.engine.capture('region', backend='niri', region=[1, 2, 30, 40]); self.assertIn('1,2 30x40', self.calls[-1])
        with self.assertRaises(ValueError): rectangle([-1, 0, 1, 1])

    def test_kde_does_not_focus_without_permission(self):
        with self.assertRaisesRegex(ValueError, 'allow_focus'): self.engine.capture('window', backend='kde', window_id=TARGET)
        self.assertEqual(self.active, OLD); self.assertFalse(any('windowactivate' in call for call in self.calls))

    def test_kde_restores_window_and_desktop_after_success_and_failure(self):
        result = self.engine.capture('window', backend='kde', window_id=TARGET, allow_focus=True)
        self.assertEqual(result['detail']['focus'], 'restored'); self.assertEqual(self.active, OLD); self.assertEqual(self.desktop, '2')
        self.fail_capture = True
        with self.assertRaisesRegex(RuntimeError, 'synthetic'): self.engine.capture('window', backend='kde', window_id=TARGET, allow_focus=True)
        self.assertEqual(self.active, OLD)

    def test_kde_respects_user_focus_changes_and_refuses_broad_region_fallback(self):
        self.interfere = True; result = self.engine.capture('window', backend='kde', window_id=TARGET, allow_focus=True)
        self.assertEqual(self.active, OTHER); self.assertEqual(result['detail']['focus'], 'not-restored-user-changed-focus-or-desktop')
        self.interfere = False; self.interfere_desktop = True; self.active = OLD; self.desktop = '2'
        desktop = self.engine.capture('window', backend='kde', window_id=TARGET, allow_focus=True)
        self.assertEqual(self.active, TARGET); self.assertEqual(self.desktop, '5'); self.assertIn('user-changed', desktop['detail']['focus'])
        before = len(self.calls)
        with self.assertRaisesRegex(ValueError, 'unsupported'): self.engine.capture('region', backend='kde', region=[0, 0, 20, 20])
        self.assertEqual(len(self.calls), before)

    def test_private_receipt_metadata_only_sharing_and_pixel_integrity(self):
        record = self.engine.capture('screen', backend='niri', output='DP-1'); image = Path(record['directory']) / 'capture.png'
        self.assertEqual(image.stat().st_mode & 0o777, 0o600); self.assertEqual(image.parent.stat().st_mode & 0o777, 0o700)
        with Image.open(image) as opened: self.assertNotIn('private-fixture', opened.info)
        _, data = self.engine.read_capture(record['id']); self.assertIsNone(data)
        meta, data = self.engine.read_capture(record['id'], share_with_model=True, crop=[0, 0, 20, 10]); self.assertEqual(meta['crop'], [0, 0, 20, 10]); self.assertTrue(data.startswith(b'\x89PNG'))
        image.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'changed'): self.engine.read_capture(record['id'])
        with self.assertRaises(ValueError): self.engine.read_capture('../../private')

    def test_storage_symlinks_and_parallel_gui_capture_fail_closed(self):
        outside = self.base / 'outside'; outside.mkdir(); self.engine.root.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'): self.engine.capture('screen', backend='niri', output='DP-1')
        self.engine.root.unlink()
        with self.engine.gui_lock():
            with self.assertRaisesRegex(RuntimeError, 'Another GUI'):
                with self.engine.gui_lock(): pass

    def test_headless_code_is_escaped_source_evidence_not_code_execution(self):
        repo = self.base / 'repo'; repo.mkdir(); (repo / 'example.mjs').write_text('const value = "<script>not execution</script>";\n')
        record = self.engine.capture('code', repo=str(repo), file='example.mjs')
        self.assertIn('&lt;script&gt;', self.html); self.assertNotIn('<script>', self.html); self.assertIn('not evidence', record['detail']['meaning']); self.assertEqual(record['detail']['focus'], 'unchanged')
        (repo / 'secret').mkdir(); (repo / 'auth.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Credential'): self.engine.capture('code', repo=str(repo), file='auth.json')
        with self.assertRaisesRegex(ValueError, 'escapes'): self.engine.capture('code', repo=str(repo), file='../other.mjs')

    def test_url_and_unknown_desktop_do_not_broaden_permissions(self):
        for url in ['file:///private', 'http://synthetic@example.test', 'http://127.0.0.1/?secret=fixture']:
            with self.assertRaises(ValueError): self.engine.capture('web', url=url)
        with patch.dict(os.environ, {'XDG_CURRENT_DESKTOP': 'unknown'}):
            with self.assertRaisesRegex(ValueError, 'supported GUI'): self.engine.capture('screen', output='DP-1')
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
