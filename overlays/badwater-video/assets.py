"""Promote verified completed native-job media into immutable project-derived assets."""

import json
import shutil
from pathlib import Path
from store import atomic_json, digest, identifier, json_text


def schema(p):
    with p.db() as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS generated_assets(id TEXT PRIMARY KEY,path TEXT,hash TEXT,size INTEGER,mtime_ns INTEGER,metadata TEXT,provenance TEXT)"
        )


def register(engine, project, job, filename):
    p = engine.project(project)
    schema(p)
    status = engine.jobs.status(identifier(job))
    if (
        status["project"] != project
        or status["state"] != "done"
        or status["operation"] != "native"
    ):
        raise ValueError(
            "generated assets must originate in a completed native job of this project"
        )
    source_job = engine.jobs.raw(job)
    app = json.loads(source_job["args"])["application"]
    if (
        not isinstance(filename, str)
        or not filename
        or Path(filename).is_absolute()
        or ".." in Path(filename).parts
    ):
        raise ValueError("native asset filename must be a relative workspace file")
    source = engine.policy.read(p.root / ".work" / job / app / filename)
    if source.stat().st_nlink != 1 or source.stat().st_size > engine.config.get(
        "maxEffectAssetBytes", 1024**3
    ):
        raise ValueError("generated asset is hardlinked or exceeds its bound")
    if source.suffix.lower() not in {
        ".mov",
        ".mp4",
        ".webm",
        ".mkv",
        ".wav",
        ".flac",
        ".png",
        ".jpg",
    }:
        raise ValueError("unsupported generated media type")
    before = source.stat()
    h = digest(source)
    metadata = engine.probe(source, derived=True)
    directory = engine.policy.write(
        p.root / "derived" / h / ("media" + source.suffix.lower())
    ).parent
    target = directory / ("media" + source.suffix.lower())
    if not target.exists():
        with source.open("rb") as src, target.open("xb") as dest:
            shutil.copyfileobj(src, dest, 1024 * 1024)
        target.chmod(0o600)
    if digest(target) != h or (before.st_size, before.st_mtime_ns) != (
        source.stat().st_size,
        source.stat().st_mtime_ns,
    ):
        raise ValueError("generated source changed during registration")
    provenance = {
        "nativeJob": job,
        "application": app,
        "source": str(source),
        "hash": h,
        "sourceKind": "derived, not a recording observation",
    }
    if not (directory / "provenance.json").exists():
        atomic_json(directory / "provenance.json", provenance)
    stat = target.stat()
    with p.db() as db:
        db.execute(
            "INSERT OR IGNORE INTO generated_assets VALUES (?,?,?,?,?,?,?)",
            (
                h,
                str(target),
                h,
                stat.st_size,
                stat.st_mtime_ns,
                json_text(metadata),
                json_text(provenance),
            ),
        )
    return {
        "asset": h,
        "hash": h,
        "kind": "generated",
        "path": str(target),
        "provenance": provenance,
    }
