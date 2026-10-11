"""Versioned local state, authority checks and rational edit decisions."""
import hashlib
import json
import math
import os
import re
import selectors
import signal
import time
import sqlite3
import stat
import subprocess
import uuid
from contextlib import contextmanager
from fractions import Fraction
from pathlib import Path

VERSION = 1
PIPELINE = "badwater-video/0.1.0"
TICKS = 254016000000
IDENTIFIER = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
MEDIA_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".wav", ".flac", ".mp3", ".m4a", ".ogg", ".aif", ".aiff", ".png", ".jpg", ".jpeg"}


def identifier(value):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError("expected a project/job/asset identifier, not a path")
    return value


def rational(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("times/rates must be exact integer or rational strings, e.g. '1/2' or '30000/1001'")
    if len(str(value)) > 64:
        raise ValueError("rational value is too large")
    result = Fraction(value)
    if abs(result) > 86400 * 30:
        raise ValueError("time/rate exceeds the supported bound")
    return result


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def json_text(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True)


def load_json(path):
    if path.stat().st_size > 1_000_000:
        raise ValueError("JSON document exceeds 1 MB")
    return json.loads(path.read_text(encoding="utf-8"))


def no_links(path):
    for component in (path, *path.parents):
        try:
            if stat.S_ISLNK(component.lstat().st_mode):
                raise ValueError("symlinks are not authorized for media/project/output paths")
        except FileNotFoundError:
            continue
    return path


def atomic_json(path, value, replace=False):
    no_links(path)
    temp = path.parent / ("." + uuid.uuid4().hex + ".tmp")
    fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json_text(value) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        publish(temp, path, replace)
    finally:
        temp.unlink(missing_ok=True)


def publish(temp, target, replace=False):
    no_links(target)
    if target.exists() and (not target.is_file() or target.stat().st_nlink != 1):
        raise ValueError("refusing to replace a non-regular or linked output")
    if replace:
        os.replace(temp, target)
    else:
        os.link(temp, target)  # Atomic no-clobber; a concurrent creator wins safely.
        temp.unlink()
    fd = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Policy:
    def __init__(self, config):
        self.config = config
        self.write_root = self._root(config["writeRoot"])
        self.read_roots = [self._root(p) for p in config["readRoots"]]
        if any(self.write_root.is_relative_to(p) or p.is_relative_to(self.write_root) for p in self.read_roots):
            raise ValueError("raw read roots and derived write root must be disjoint")
        if type(config.get("concurrency", 1)) is not int or type(config.get("timeoutSeconds", 1200)) is not int or not 1 <= config.get("concurrency", 1) <= 4 or not 30 <= config.get("timeoutSeconds", 1200) <= 7200:
            raise ValueError("concurrency must be integer 1..4 and job deadline integer 30..7200 seconds")
        if type(config.get("maxAutomaticRepairAttempts", 2)) is not int or not 0 <= config.get("maxAutomaticRepairAttempts", 2) <= 3:
            raise ValueError("automatic repair budget must be integer 0..3")

    @staticmethod
    def _root(value):
        p = Path(value)
        if not p.is_absolute() or ".." in p.parts or p == Path("/"):
            raise ValueError("authorization roots must be absolute, non-root paths without traversal")
        return no_links(p)

    def read(self, value, raw=False):
        p = self._root(value)
        roots = self.read_roots if raw else [*self.read_roots, self.write_root]
        if not any(p.is_relative_to(root) for root in roots):
            raise ValueError("path is outside authorized read roots")
        if not p.is_file() or p.stat().st_size == 0:
            raise ValueError("input is missing, empty, or not a regular file")
        return p

    def write(self, value):
        p = self._root(value)
        if not p.is_relative_to(self.write_root) or p == self.write_root:
            raise ValueError("path is outside the derived write root")
        no_links(p.parent)
        p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        return p

    def sandbox(self, argv, cwd=None):
        c = self.config
        args = [c["bubblewrap"], "--unshare-all", "--die-with-parent", "--new-session",
                "--ro-bind", "/nix/store", "/nix/store", "--proc", "/proc", "--dev", "/dev",
                "--tmpfs", "/tmp", "--dir", "/tmp/home", "--dir", "/tmp/config",
                "--dir", "/tmp/data", "--dir", "/tmp/cache", "--dir", "/tmp/runtime",
                "--dir", "/bin", "--ro-bind", c["bash"], "/bin/sh", "--clearenv",
                "--setenv", "HOME", "/tmp/home", "--setenv", "XDG_CONFIG_HOME", "/tmp/config",
                "--setenv", "XDG_DATA_HOME", "/tmp/data", "--setenv", "XDG_CACHE_HOME", "/tmp/cache",
                "--setenv", "XDG_RUNTIME_DIR", "/tmp/runtime", "--setenv", "TMPDIR", "/tmp",
                "--setenv", "PATH", c["toolPath"], "--setenv", "RAYON_NUM_THREADS", "3",
                "--setenv", "OMP_NUM_THREADS", "3"]
        for root in self.read_roots:
            if root.exists():
                no_links(root)
                args += ["--ro-bind", str(root), str(root)]
        self.write_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        no_links(self.write_root)
        args += ["--bind", str(self.write_root), str(self.write_root), "--remount-ro", "/", "--chdir", str(cwd or self.write_root)]
        return [*args, *argv]

    def run(self, argv, cwd=None, timeout=60):
        # Fail rather than silently truncate observations or accumulate unbounded child output.
        buffers = {"stdout": bytearray(), "stderr": bytearray()}
        child = subprocess.Popen(self.sandbox(argv, cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        selector = selectors.DefaultSelector()
        try:
            for name in buffers:
                selector.register(getattr(child, name), selectors.EVENT_READ, name)
            deadline = time.monotonic() + timeout
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise RuntimeError("child deadline exceeded; owned process group stopped")
                for key, _ in selector.select(min(remaining, 0.2)):
                    block = os.read(key.fd, 65536)
                    if not block:
                        selector.unregister(key.fileobj)
                        continue
                    output = buffers[key.data]
                    if len(output) + len(block) > 8 * 1024 * 1024:
                        raise RuntimeError(f"child {key.data} exceeds 8 MiB; refusing incomplete observations/logs")
                    output.extend(block)
            status = child.wait(timeout=max(0.01, deadline - time.monotonic()))
            if status:
                raise RuntimeError(f"child exited {status}: " + buffers["stderr"][-4000:].decode("utf-8", "replace"))
            return bytes(buffers["stdout"]), bytes(buffers["stderr"])
        finally:
            selector.close()
            if child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait(timeout=5)
            child.stdout.close()
            child.stderr.close()


class Project:
    def __init__(self, policy, name, create=False):
        self.policy = policy
        self.name = identifier(name)
        self.root = policy.write(policy.write_root / name / "index.sqlite").parent
        self.path = self.root / "index.sqlite"
        if not create and not self.path.is_file():
            raise ValueError("project not found; create it explicitly")
        if create and self.path.exists():
            raise ValueError("project already exists; use project open")
        with self.db() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if create:
                db.executescript("""
                    CREATE TABLE info(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                    CREATE TABLE assets(id TEXT PRIMARY KEY, path TEXT NOT NULL, hash TEXT NOT NULL, size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL, metadata TEXT NOT NULL);
                    CREATE TABLE observations(asset TEXT NOT NULL, cache_key TEXT NOT NULL, body TEXT NOT NULL, PRIMARY KEY(asset,cache_key));
                    CREATE VIRTUAL TABLE transcript USING fts5(asset UNINDEXED, cache_key UNINDEXED, start UNINDEXED, end UNINDEXED, text);
                    CREATE TABLE revisions(id INTEGER PRIMARY KEY, parent INTEGER, plan TEXT NOT NULL, native_path TEXT NOT NULL, native_hash TEXT NOT NULL);
                    PRAGMA user_version=1;
                """)
                db.execute("INSERT INTO info VALUES ('remoteConsent','false')")
            elif version != VERSION:
                raise ValueError(f"unsupported index version {version}; refusing migration/data loss")

    @contextmanager
    def db(self):
        no_links(self.path)
        if self.path.exists() and self.path.stat().st_nlink != 1:
            raise ValueError("refusing a hard-linked project database")
        db = sqlite3.connect(self.path, timeout=5)
        try:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA foreign_keys=ON")
            os.chmod(self.path, 0o600)
            with db:
                yield db
        finally:
            db.close()

    def summary(self):
        with self.db() as db:
            return {"project": self.name, "indexVersion": VERSION,
                    "assets": db.execute("SELECT COUNT(*) FROM assets").fetchone()[0],
                    "revision": db.execute("SELECT MAX(id) FROM revisions").fetchone()[0],
                    "remoteConsent": json.loads(db.execute("SELECT value FROM info WHERE key='remoteConsent'").fetchone()[0])}

    def asset(self, asset_id, verify=False):
        identifier(asset_id)
        with self.db() as db:
            row = db.execute("SELECT * FROM assets WHERE id=?", (asset_id,)).fetchone()
        if row is None:
            raise ValueError("asset not indexed in this project")
        result = dict(row)
        p = self.policy.read(result["path"], raw=True)
        s = p.stat()
        if s.st_size != result["size"] or s.st_mtime_ns != result["mtime_ns"] or (verify and digest(p) != result["hash"]):
            raise ValueError("asset changed; ingest again to assign its new content identity")
        result["metadata"] = json.loads(result["metadata"])
        return result

    def validate(self, plan):
        allowed = {"version", "output", "clips", "constraints", "audio", "notes"}
        if set(plan) - allowed or type(plan.get("version")) is not int or plan.get("version") != 1:
            raise ValueError("unsupported plan version/fields (captions/effects/multicamera are not implemented)")
        out = plan["output"]
        if set(out) - {"width", "height", "fps", "aspect"}:
            raise ValueError("unknown output setting")
        w, h = out["width"], out["height"]
        if type(w) is not int or type(h) is not int or not 16 <= w <= 3840 or not 16 <= h <= 2160 or w % 2 or h % 2:
            raise ValueError("output must have even dimensions, 16..3840 by 16..2160")
        fps = rational(out["fps"])
        if not 1 <= fps <= 60 or (out.get("aspect") and Fraction(w, h) != rational(out["aspect"])):
            raise ValueError("frame rate/aspect ratio is invalid or inconsistent")
        clips = plan["clips"]
        if not isinstance(clips, list) or not 1 <= len(clips) <= 200:
            raise ValueError("a plan requires 1..200 cuts")
        cursor = Fraction(0)
        ranges = []
        for clip in clips:
            if set(clip) != {"asset", "in", "out", "reason"} or not isinstance(clip["reason"], str) or not 1 <= len(clip["reason"]) <= 1000:
                raise ValueError("each clip requires an asset, exact in/out seconds and a bounded editorial reason")
            asset = self.asset(clip["asset"])
            if not any(s["codec_type"] == "video" for s in asset["metadata"]["streams"]):
                raise ValueError("timeline video cuts require a video asset")
            start, end = rational(clip["in"]), rational(clip["out"])
            if not 0 <= start < end <= rational(asset["metadata"]["duration"]):
                raise ValueError("source range is outside the indexed duration")
            ranges.append({"asset": clip["asset"], "in": str(start), "out": str(end), "timelineIn": str(cursor), "timelineOut": str(cursor + end - start), "reason": clip["reason"]})
            cursor += end - start
        if cursor > 3600:
            raise ValueError("first-slice exports are bounded to one hour")
        constraints = plan.get("constraints", {})
        if set(constraints) - {"targetDuration", "tolerance", "maxCutSeconds", "mustInclude", "mustExclude"}:
            raise ValueError("unknown editorial constraint")
        tolerance = rational(constraints.get("tolerance", str(1 / fps)))
        if tolerance < 0 or ("targetDuration" in constraints and abs(cursor - rational(constraints["targetDuration"])) > tolerance):
            raise ValueError("edit does not meet the requested duration")
        if "maxCutSeconds" in constraints and any(rational(r["out"]) - rational(r["in"]) > rational(constraints["maxCutSeconds"]) for r in ranges):
            raise ValueError("edit exceeds the requested maximum shot length")
        for mode in ("mustInclude", "mustExclude"):
            for required in constraints.get(mode, []):
                asset = self.asset(required["asset"])
                a, b = rational(required["in"]), rational(required["out"])
                if not 0 <= a < b <= rational(asset["metadata"]["duration"]):
                    raise ValueError("constraint range is invalid")
                selected = sorted((rational(r["in"]), rational(r["out"])) for r in ranges if r["asset"] == required["asset"])
                if mode == "mustExclude" and any(x < b and y > a for x, y in selected):
                    raise ValueError("edit includes an excluded source range")
                if mode == "mustInclude":
                    covered = a
                    for x, y in selected:
                        if x <= covered:
                            covered = max(covered, y)
                    if covered < b:
                        raise ValueError("edit misses a required source range")
        audio = plan.get("audio", {})
        if set(audio) - {"microphone", "offset", "normalize"} or type(audio.get("normalize", False)) is not bool:
            raise ValueError("unknown/invalid audio setting")
        if "microphone" in audio:
            mic = self.asset(audio["microphone"])
            if not any(s["codec_type"] == "audio" for s in mic["metadata"]["streams"]):
                raise ValueError("microphone asset has no audio stream")
            offset = rational(audio.get("offset", "0"))
            if any(rational(r["in"]) + offset < 0 or rational(r["out"]) + offset > rational(mic["metadata"]["duration"]) for r in ranges):
                raise ValueError("aligned microphone source range is out of bounds")
            if len({r["asset"] for r in ranges}) != 1:
                raise ValueError("separate microphone alignment currently supports one camera asset; align each recording explicitly")
        return {"valid": True, "duration": str(cursor), "output": out, "ranges": ranges, "audio": audio, "pipeline": PIPELINE, "semantics": "source seconds; half-open ranges; exact rational decisions; native ticks rounded within half a tick"}
