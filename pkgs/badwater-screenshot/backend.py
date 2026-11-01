"""Bounded capture operations. Importing this module never queries a desktop."""
import contextlib
import fcntl
import hashlib
import html
import http.server
import io
import json
import os
import re
import stat
import subprocess
import threading
import time
import urllib.parse
import uuid
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = 32_000_000
MAX_BYTES = 24 * 1024 * 1024
ID = re.compile(r'[0-9a-f]{32}')
KWIN_ID = re.compile(r'\{[0-9a-fA-F-]{36}\}')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def private_dir(path):
    path = Path(path).absolute()
    for parent in [path, *path.parents]:
        if parent.exists() or parent.is_symlink():
            require(not parent.is_symlink(), 'Refusing symlinked capture storage')
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    require(path.stat().st_uid == os.getuid(), 'Capture storage is not owned by this user')
    path.chmod(0o700)
    return path


def save_json(path, value):
    data = json.dumps(value, indent=2, ensure_ascii=False) + '\n'
    require(len(data.encode()) < 256 * 1024, 'Capture metadata is too large')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(data)


def rectangle(value):
    require(isinstance(value, list) and len(value) == 4 and all(type(n) is int for n in value), 'Region must be [x,y,width,height] integers')
    x, y, width, height = value
    require(min(x, y) >= 0 and 0 < width <= 16384 and 0 < height <= 16384 and width * height <= 32_000_000, 'Region is out of bounds')
    return x, y, width, height


class CaptureEngine:
    def __init__(self, paths, state_root=None, command_runner=None):
        self.paths = paths
        self._command_runner = command_runner
        self.root = Path(state_root or os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'badwater-screenshot'

    def command(self, argv, timeout=15):
        if self._command_runner is not None:
            return self._command_runner(argv, timeout=timeout)
        result = subprocess.run(argv, capture_output=True, timeout=timeout, check=False)
        require(len(result.stdout) <= 2 * 1024 * 1024 and len(result.stderr) <= 2 * 1024 * 1024, 'Backend output exceeds its bound')
        if result.returncode:
            raise RuntimeError(f'{Path(argv[0]).name} failed (exit {result.returncode}); no broader capture fallback was attempted')
        return result.stdout.decode('utf-8', errors='replace').strip()

    def desktop(self, backend):
        if backend == 'auto':
            desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
            backend = 'niri' if 'niri' in desktop else 'kde' if 'kde' in desktop else 'unavailable'
        require(backend in ['niri', 'kde'], 'No supported GUI session; use headless web/code or select an authorized niri/kde session')
        return backend

    def capabilities(self):
        return {'name': 'badwater-screenshot', 'modes': ['web', 'code', 'window', 'screen', 'region'],
                'headless': 'fresh isolated Chromium; no personal profile, cookies or CDP',
                'gui': {'niri': 'window by ID without focus (clipboard opt-in); output/region via grim', 'kde': 'Spectacle; window focus only with opt-in and best-effort restoration; screen all/current'},
                'region': 'niri/grim only; unsupported backends fail rather than capture a broader area',
                'sharing': 'capture returns metadata only; read_capture needs share_with_model=true after operator approval',
                'state': str(self.root), 'startup_capture': False}

    def targets(self, backend='auto', pid=None, include_titles=False):
        backend = self.desktop(backend)
        require(pid is None or type(pid) is int and pid > 0, 'PID must be a positive integer')
        if backend == 'niri':
            windows = json.loads(self.command([self.paths['niri'], 'msg', '--json', 'windows']))
            outputs = json.loads(self.command([self.paths['niri'], 'msg', '--json', 'outputs']))
            filtered = [w for w in windows if pid is None or w.get('pid') == pid]
            result = []
            for w in filtered[:50]:
                item = {key: w.get(key) for key in ['id', 'app_id', 'pid', 'is_focused', 'workspace_id']}
                if include_titles:
                    item['title'] = w.get('title')
                result.append(item)
            return {'backend': backend, 'windows': result, 'outputs': list(outputs), 'truncated': len(filtered) > 50}
        argv = [self.paths['kdotool'], 'search']
        if pid is not None:
            argv += ['--pid', str(pid)]
        ids = self.command([*argv, '--limit', '50', '.*']).splitlines()
        result = []
        for window_id in ids:
            require(KWIN_ID.fullmatch(window_id), 'KDE returned an unsupported window ID')
            item = {'id': window_id}
            if include_titles:
                item['title'] = self.command([self.paths['kdotool'], 'getwindowname', window_id])
            result.append(item)
        return {'backend': backend, 'windows': result, 'outputs': ['all', 'current']}

    @contextlib.contextmanager
    def gui_lock(self):
        root = private_dir(self.root)
        fd = os.open(root / 'gui.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            require(info.st_uid == os.getuid() and info.st_nlink == 1 and stat.S_ISREG(info.st_mode), 'Invalid GUI lock ownership/type')
            os.fchmod(fd, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError('Another GUI capture is active; do not race desktop focus') from exc
            yield
        finally:
            os.close(fd)

    def wait_png(self, path):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if path.exists():
                require(not path.is_symlink() and path.stat().st_nlink == 1 and path.stat().st_size <= MAX_BYTES, 'Invalid/oversized backend image')
                try:
                    with Image.open(path) as image:
                        image.verify()
                    return
                except (OSError, SyntaxError):
                    pass
            time.sleep(0.05)
        raise RuntimeError('Backend did not finish a valid PNG before the deadline')

    def normalize(self, source, target):
        self.wait_png(source)
        with Image.open(source) as image:
            require(0 < image.width * image.height <= 32_000_000, 'Image pixel count exceeds limit')
            image.convert('RGB').save(target, format='PNG')
        target.chmod(0o600)
        require(target.stat().st_size <= MAX_BYTES, 'PNG exceeds capture byte limit')
        with Image.open(target) as image:
            width, height = image.size
        return {'file': target.name, 'width': width, 'height': height, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'bytes': target.stat().st_size}

    def web(self, directory, url, allow_origins):
        parsed = urllib.parse.urlsplit(url)
        require(parsed.scheme in ['http', 'https'] and parsed.hostname and not parsed.username and not parsed.password, 'Only explicit HTTP(S) URLs without credentials are allowed')
        require(not parsed.query and not parsed.fragment, 'Do not put credentials/state in capture URL queries/fragments; use an authorized window for existing state')
        require(isinstance(allow_origins, list) and len(allow_origins) <= 10 and all(isinstance(v, str) for v in allow_origins), 'Invalid origin authorization list')
        argv = [self.paths['browser'], '--url', url, '--output', str(directory / 'web')]
        for origin in allow_origins:
            argv += ['--allow-origin', origin]
        self.command(argv, timeout=70)
        report = json.loads((directory / 'web/report.json').read_text())
        return {name: self.normalize(directory / 'web' / f'{name}.png', directory / f'{name}.png') for name in ['desktop', 'mobile']}, report

    def code(self, directory, repo, file, start_line, end_line):
        require(isinstance(repo, str) and Path(repo).is_absolute() and isinstance(file, str), 'Code capture requires an absolute approved repo and relative file')
        relative = Path(file)
        require(not relative.is_absolute() and '..' not in relative.parts and '.git' not in relative.parts, 'Code path escapes its repository')
        root = Path(repo).resolve(strict=True)
        current = root
        for part in relative.parts:
            current = current / part
            require(not current.is_symlink(), 'Code path must not traverse symlinks')
        require(current.is_file() and current.stat().st_size <= 1024 * 1024, 'Code file is unavailable or too large')
        require(not any(part.startswith('.env') or part.lower() in ['auth.json', 'mcp-auth.json', 'id_rsa', 'id_ed25519', 'secrets', '.ssh', '.gnupg'] for part in relative.parts), 'Credential/private paths are not code screenshot targets')
        require(current.suffix.lower() in ['.nix', '.py', '.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx', '.rs', '.go', '.c', '.cpp', '.h', '.java', '.sh', '.md', '.css', '.html', '.json', '.yaml', '.yml', '.toml'], 'Unsupported code/text file type')
        data = current.read_bytes(); lines = data.decode('utf-8').splitlines()
        require(type(start_line) is int and start_line > 0, 'Start line must be a positive integer')
        end_line = min(len(lines), start_line + 29) if end_line is None else end_line
        require(type(start_line) is int and type(end_line) is int and 1 <= start_line <= end_line <= len(lines) and end_line - start_line < 40, 'Choose a valid range of at most40 source lines')
        rows = '\n'.join(f'{i:>4}  {lines[i - 1]}' for i in range(start_line, end_line + 1))
        content = ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Approved source excerpt</title>'
                   '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
                   '<style>body{background:#111827;color:#e5e7eb;margin:0;padding:28px;font:14px/20px "DejaVu Sans Mono",monospace}h1{font:18px/24px "DejaVu Sans",sans-serif;color:#93c5fd}pre{font:inherit;white-space:pre-wrap;overflow-wrap:anywhere;padding:20px;background:#1f2937;border-radius:12px}</style>'
                   f'<h1>{html.escape(file)} · lines {start_line}–{end_line}</h1><pre>{html.escape(rows)}</pre></html>').encode()
        nonce = uuid.uuid4().hex
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != '/' + nonce:
                    self.send_error(404); return
                self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.send_header('Content-Length', str(len(content))); self.end_headers(); self.wfile.write(content)
            def log_message(self, format: str, *args: object) -> None:
                pass
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            images, _ = self.web(directory, f'http://127.0.0.1:{server.server_port}/{nonce}', [])
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)
        return images, {'file': file, 'start_line': start_line, 'end_line': end_line, 'source_sha256': hashlib.sha256(data).hexdigest(), 'meaning': 'rendered source text, not evidence that code executed; fixed viewport may wrap/clip long lines'}

    def gui(self, directory, kind, backend, window_id, output, region, allow_focus, allow_clipboard_change):
        backend = self.desktop(backend)
        target = directory / 'backend.png'
        receipt = {'backend': backend, 'focus': 'unchanged', 'clipboard': 'unchanged'}
        with self.gui_lock():
            if backend == 'niri':
                if kind == 'window':
                    require(isinstance(window_id, str) and window_id.isdigit() and 0 < int(window_id) < 2**64, 'Niri capture requires an explicit numeric window ID')
                    require(allow_clipboard_change is True, 'Niri native window capture also replaces the clipboard; explicit allow_clipboard_change is required, or use headless/output capture')
                    self.command([self.paths['niri'], 'msg', 'action', 'screenshot-window', '--id', window_id, '--show-pointer', 'false', '--path', str(target)])
                    receipt.update({'window_id': window_id, 'clipboard': 'changed-by-explicit-permission'})
                else:
                    argv = [self.paths['grim'], '-t', 'png']
                    if kind == 'screen':
                        require(isinstance(output, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', output), 'Choose an explicit output from authorized target discovery')
                        argv += ['-o', output]; receipt['output'] = output
                    else:
                        x, y, width, height = rectangle(region); argv += ['-g', f'{x},{y} {width}x{height}']; receipt['region'] = region
                    self.command([*argv, str(target)])
            else:
                require(kind != 'region', 'Noninteractive KDE region capture is unsupported; no full-screen crop fallback is permitted')
                args = [self.paths['spectacle'], '--background', '--nonotify', '--new-instance', '--output', str(target)]
                if kind == 'screen':
                    require(output in ['all', 'current'], 'KDE screen target must be explicitly all or current')
                    self.command([*args, '--fullscreen' if output == 'all' else '--current']); receipt['output'] = output
                else:
                    require(isinstance(window_id, str) and KWIN_ID.fullmatch(window_id), 'KDE capture requires an explicit window UUID')
                    old = self.command([self.paths['kdotool'], 'getactivewindow'])
                    desktop = self.command([self.paths['kdotool'], 'get_desktop'])
                    require(KWIN_ID.fullmatch(old) and desktop.isdigit() and int(desktop) > 0, 'Cannot safely record the original KDE window/desktop')
                    require(old == window_id or allow_focus is True, 'Target is not focused; approve allow_focus or use headless/Niri capture')
                    moved = old != window_id
                    expected_desktop = None
                    try:
                        if moved:
                            save_json(directory / 'focus-before.json', {'window_id': old, 'desktop': desktop, 'target': window_id})
                            self.command([self.paths['kdotool'], 'windowactivate', window_id]); receipt['focus'] = 'temporarily-changed'
                        require(self.command([self.paths['kdotool'], 'getactivewindow']) == window_id, 'Target did not gain focus; refusing the wrong-window screenshot')
                        expected_desktop = self.command([self.paths['kdotool'], 'get_desktop'])
                        self.command([*args, '--activewindow', '--no-decoration', '--no-shadow'])
                    finally:
                        if moved:
                            current = self.command([self.paths['kdotool'], 'getactivewindow'])
                            if current == window_id and (expected_desktop is None or self.command([self.paths['kdotool'], 'get_desktop']) == expected_desktop):
                                self.command([self.paths['kdotool'], 'windowactivate', old]); self.command([self.paths['kdotool'], 'set_desktop', desktop])
                                require(self.command([self.paths['kdotool'], 'getactivewindow']) == old, 'Capture finished but original focus restoration failed')
                                receipt['focus'] = 'restored'
                            else:
                                receipt['focus'] = 'not-restored-user-changed-focus-or-desktop'
                    receipt['window_id'] = window_id
            images = {'capture': self.normalize(target, directory / 'capture.png')}
        return images, receipt

    def capture(self, kind, *, url=None, allow_origins=None, repo=None, file=None, start_line=1, end_line=None, backend='auto', window_id=None, output=None, region=None, allow_focus=False, allow_clipboard_change=False):
        require(kind in ['web', 'code', 'window', 'screen', 'region'], 'Unknown capture kind')
        directory = private_dir(private_dir(self.root / 'captures') / uuid.uuid4().hex)
        capture_id = directory.name
        try:
            if kind == 'web':
                require(isinstance(url, str), 'Web capture requires an explicit authorized URL')
                images, report = self.web(directory, url, allow_origins or [])
                observations = [{key: item.get(key) for key in ['name', 'viewport', 'httpStatus']} | {'final_url': urllib.parse.urlunsplit(urllib.parse.urlsplit(item.get('finalURL', url))._replace(query='', fragment=''))} for item in report.get('captures', [])]
                detail = {'backend': 'isolated-chromium', 'url': url, 'observations': observations, 'focus': 'unchanged', 'state': 'fresh profile; not the existing browser tab/cookies'}
            elif kind == 'code':
                images, detail = self.code(directory, repo, file, start_line, end_line); detail['backend'] = 'isolated-chromium-code'; detail['focus'] = 'unchanged'
            else:
                images, detail = self.gui(directory, kind, backend, window_id, output, region, allow_focus, allow_clipboard_change)
            record = {'version': 1, 'id': capture_id, 'kind': kind, 'captured_at': datetime.now(UTC).isoformat(), 'detail': detail, 'images': images, 'sharing': 'metadata only; pixels require a separate explicit read_capture sharing decision'}
            save_json(directory / 'capture.json', record)
            return {**record, 'directory': str(directory)}
        except Exception as exc:
            save_json(directory / 'error.json', {'id': capture_id, 'kind': kind, 'error': type(exc).__name__, 'message': str(exc)[:1000]})
            raise
        finally:
            for path in directory.rglob('*'):
                if path.is_file() and not path.is_symlink():
                    path.chmod(0o600)

    def read_capture(self, capture_id, image='capture', share_with_model=False, crop=None):
        require(isinstance(capture_id, str) and ID.fullmatch(capture_id), 'Invalid capture ID')
        private_dir(self.root)
        require((self.root / 'captures').is_dir() and not (self.root / 'captures').is_symlink(), 'Unknown capture storage')
        directory = self.root / 'captures' / capture_id
        require(directory.is_dir() and not directory.is_symlink() and directory.stat().st_uid == os.getuid(), 'Unknown capture')
        metadata = directory / 'capture.json'
        require(metadata.is_file() and not metadata.is_symlink() and metadata.stat().st_nlink == 1 and metadata.stat().st_size <= 256 * 1024, 'Invalid capture metadata')
        record = json.loads(metadata.read_text())
        require(image in record['images'], 'Choose an image listed in this capture')
        info = record['images'][image]; source = directory / info['file']
        require(source.parent == directory and source.is_file() and not source.is_symlink() and source.stat().st_nlink == 1 and source.stat().st_size <= MAX_BYTES, 'Invalid capture artifact')
        require(hashlib.sha256(source.read_bytes()).hexdigest() == info['sha256'], 'Capture bytes changed; do not treat them as original evidence')
        if share_with_model is not True:
            return {'record': record, 'image': image, 'pixels': 'not shared'}, None
        with Image.open(source) as opened:
            if crop is not None:
                x, y, width, height = rectangle(crop); require(x + width <= opened.width and y + height <= opened.height, 'Crop escapes the captured image'); opened = opened.crop((x, y, x + width, y + height))
            stream = io.BytesIO(); opened.convert('RGB').save(stream, format='PNG'); data = stream.getvalue()
        require(len(data) <= 10 * 1024 * 1024, 'Image too large for model sharing; choose an explicit crop')
        return {'record': record, 'image': image, 'crop': crop, 'sharing': 'explicit image-input permission required'}, data
