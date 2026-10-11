"""Persist source-backed editorial decisions and resumable deliverable manifests, not provider calls."""

import hashlib
import json
from fractions import Fraction
from pathlib import Path
from store import digest, identifier, json_text, rational
import evidence

KINDS = {"topic", "moment", "speaker-turn", "chapter", "quote", "review"}


def schema(p):
    with p.db() as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS editorial_context(id TEXT PRIMARY KEY, asset TEXT, start TEXT, end TEXT, body TEXT)"
        )
        db.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS editorial_context_fts USING fts5(id UNINDEXED, asset UNINDEXED, text)"
        )
        db.execute(
            "CREATE TABLE IF NOT EXISTS editorial_batches(id TEXT PRIMARY KEY, body TEXT, state TEXT)"
        )


def annotate(engine, project, item):
    p = engine.project(project)
    schema(p)
    if not p.summary()["remoteConsent"]:
        raise ValueError(
            "media-derived editorial notes require model-sharing permission"
        )
    if not isinstance(item, dict) or set(item) - {
        "asset",
        "in",
        "out",
        "kind",
        "summary",
        "cacheKey",
        "wordIds",
        "frameSeconds",
        "tags",
        "uncertainty",
    }:
        raise ValueError("unknown editorial context fields")
    if (
        item.get("kind") not in KINDS
        or not isinstance(item.get("summary"), str)
        or not 1 <= len(item["summary"].encode()) <= 4000
    ):
        raise ValueError("context requires a known kind and 1..4000 UTF-8 bytes")
    a = p.asset(item["asset"])
    start, end = rational(item["in"]), rational(item["out"])
    if not 0 <= start < end <= rational(a["metadata"]["duration"]):
        raise ValueError("editorial context source range is invalid")
    words = item.get("wordIds", [])
    frames = item.get("frameSeconds", [])
    if (
        not isinstance(words, list)
        or len(words) > 500
        or any(type(x) is not int or x < 0 for x in words)
        or not isinstance(frames, list)
        or len(frames) > 40
    ):
        raise ValueError(
            "context references are bounded to 500 word ids and 40 sampled frames"
        )
    if words:
        data = evidence.read(engine, project, a["id"], item["cacheKey"])
        ids = {w["id"]: w for w in data["words"]}
        if any(
            w not in ids
            or rational(ids[w]["start"]) < start
            or rational(ids[w]["end"]) > end
            for w in words
        ):
            raise ValueError(
                "context words must belong to the referenced source range/cache"
            )
    if frames:
        import review

        with p.db() as db:
            review.schema(db)
            for when in frames:
                t = rational(when)
                if (
                    not start <= t < end
                    or not db.execute(
                        "SELECT 1 FROM visual_frames WHERE asset=? AND seconds=? AND attachments>0",
                        (a["id"], str(t)),
                    ).fetchone()
                ):
                    raise ValueError(
                        "context frames must be previously permission-shared samples in this interval"
                    )
    if not words and not frames:
        raise ValueError(
            "context needs source word ids or reviewed frame references; do not invent observations"
        )
    if len(json_text(item).encode()) > 12000:
        raise ValueError("context exceeds 12 KiB")
    key = hashlib.sha256(json_text(item).encode()).hexdigest()
    with p.db() as db:
        inserted = db.execute(
            "INSERT OR IGNORE INTO editorial_context VALUES (?,?,?,?,?)",
            (key, a["id"], str(start), str(end), json_text(item)),
        ).rowcount
        if inserted:
            db.execute(
                "INSERT INTO editorial_context_fts VALUES (?,?,?)",
                (key, a["id"], item["summary"]),
            )
    return {
        "context": key,
        "kind": item["kind"],
        "status": "source-backed model inference, not verified ground truth",
    }


def contexts(engine, project, asset, offset=0, limit=10):
    p = engine.project(project)
    p.asset(asset)
    schema(p)
    if not p.summary()["remoteConsent"]:
        raise ValueError("editorial context requires model-sharing permission")
    if (
        type(offset) is not int
        or offset < 0
        or type(limit) is not int
        or not 1 <= limit <= 20
    ):
        raise ValueError("context pages require limit 1..20")
    with p.db() as db:
        rows = [
            {"id": r["id"], **json.loads(r["body"])}
            for r in db.execute(
                "SELECT id,body FROM editorial_context WHERE asset=? ORDER BY rowid LIMIT ? OFFSET ?",
                (asset, limit, offset),
            )
        ]
    if len(json_text(rows).encode()) > 8000:
        raise ValueError("context page exceeds 8 KiB; request fewer entries")
    return {
        "contexts": rows,
        "nextOffset": offset + len(rows) if len(rows) == limit else None,
        "trust": "media-derived model inference",
    }


def search(engine, project, phrase, limit=10):
    p = engine.project(project)
    schema(p)
    if not p.summary()["remoteConsent"]:
        raise ValueError("editorial topic/idea text requires model-sharing permission")
    if (
        not isinstance(phrase, str)
        or not 1 <= len(phrase) <= 200
        or type(limit) is not int
        or not 1 <= limit <= 20
    ):
        raise ValueError("context search requires a literal phrase and limit 1..20")
    query = '"' + phrase.replace('"', '""') + '"'
    with p.db() as db:
        rows = [
            {"id": r["id"], **json.loads(r["body"])}
            for r in db.execute(
                "SELECT c.id,c.body FROM editorial_context c JOIN editorial_context_fts f ON c.id=f.id WHERE editorial_context_fts MATCH ? LIMIT ?",
                (query, limit),
            )
        ]
    for row in rows:
        p.asset(row["asset"])
    if len(json_text(rows).encode()) > 8000:
        raise ValueError("context search page exceeds 8 KiB")
    return {
        "contexts": rows,
        "searchKind": "literal source-backed topic/idea notes; inferred, not certified semantic search",
    }


def candidates(engine, project, asset, key, offset=0, limit=10):
    data = evidence.read(engine, project, asset, key)
    if (
        type(offset) is not int
        or offset < 0
        or type(limit) is not int
        or not 1 <= limit <= 20
    ):
        raise ValueError("candidate pages require limit 1..20")
    rows = data["candidates"][offset : offset + limit]
    return {
        "candidates": rows,
        "nextOffset": offset + len(rows)
        if offset + len(rows) < len(data["candidates"])
        else None,
        "meaning": "inspect setup, event, result and reaction; loudness/change is not entertainment value",
    }


def check(engine, project, plan):
    p = engine.project(project)
    validation = p.validate(plan)
    findings = []
    for cut in validation["ranges"]:
        if cut.get("track", 1) != 1:
            continue
        schema(p)
        evidence.schema(p)
        with p.db() as db:
            rows = db.execute(
                "SELECT cache_key FROM editorial_evidence WHERE asset=? ORDER BY rowid DESC LIMIT 1",
                (cut["asset"],),
            ).fetchall()
        if rows:
            data = evidence.read(engine, project, cut["asset"], rows[0]["cache_key"])
            for edge in ["in", "out"]:
                t = rational(cut[edge])
                crossing = [
                    w
                    for w in data["words"]
                    if rational(w["start"]) < t < rational(w["end"])
                ]
                if crossing:
                    findings.append(
                        {
                            "kind": "cut-through-word",
                            "asset": cut["asset"],
                            "edge": edge,
                            "seconds": str(t),
                            "wordIds": [w["id"] for w in crossing],
                        }
                    )
            if cut.get("speed", "1") != "1" and any(
                rational(w["start"]) < rational(cut["out"])
                and rational(w["end"]) > rational(cut["in"])
                for w in data["words"]
            ):
                findings.append(
                    {
                        "kind": "retimed-speech-needs-listening-review",
                        "asset": cut["asset"],
                    }
                )
    if plan.get("captions"):
        for word in plan["captions"].get("words", []):
            if len(word.get("text", "")) > 40:
                findings.append({"kind": "long-caption-word", "start": word.get("in")})
    return {
        "findings": findings,
        "mechanicalPassed": not any(x["kind"] == "cut-through-word" for x in findings),
        "requiredHumanOrModelReview": [
            "setup/payoff intact",
            "quotation qualifiers preserved",
            "distinct worthwhile idea",
            "framing/HUD/face visibility",
            "caption spelling/timing/contrast",
            "speech intelligible",
            "effects/music serve the brief",
        ],
        "editorialQualityCertified": False,
    }


def save_batch(engine, project, name, items, brief):
    p = engine.project(project)
    schema(p)
    identifier(name)
    if (
        not isinstance(items, list)
        or not 1 <= len(items) <= 50
        or not isinstance(brief, str)
        or not 1 <= len(brief.encode()) <= 4000
    ):
        raise ValueError(
            "batch requires 1..50 deliverables and a bounded editorial brief"
        )
    names, signatures, source_sets = set(), set(), []
    for item in items:
        if set(item) != {"name", "title", "plan", "contexts"}:
            raise ValueError("deliverable requires name,title,plan,contexts")
        identifier(item["name"])
        if (
            item["name"] in names
            or not isinstance(item["title"], str)
            or not 1 <= len(item["title"]) <= 200
        ):
            raise ValueError("unique names and bounded titles required")
        names.add(item["name"])
        validation = p.validate(item["plan"])
        signature = tuple(
            (r["asset"], r["in"], r["out"])
            for r in validation["ranges"]
            if r.get("track", 1) == 1
        )
        if signature in signatures:
            raise ValueError(
                "duplicate source excerpts in batch; find genuinely distinct moments"
            )
        signatures.add(signature)
        for prior in source_sets:
            overlap = sum(
                max(
                    Fraction(0),
                    min(rational(b), rational(d)) - max(rational(a), rational(c)),
                )
                for asset, a, b in signature
                for other, c, d in prior
                if asset == other
            )
            shorter = min(
                sum(rational(b) - rational(a) for _, a, b in signature),
                sum(rational(d) - rational(c) for _, c, d in prior),
            )
            if shorter and overlap / shorter >= Fraction(4, 5):
                raise ValueError(
                    "batch excerpts overlap by at least 80%; find distinct ideas rather than quota padding"
                )
        source_sets.append(signature)
        if (
            not isinstance(item["contexts"], list)
            or not 1 <= len(item["contexts"]) <= 20
        ):
            raise ValueError(
                "each deliverable needs 1..20 source-backed context decisions"
            )
        with p.db() as db:
            for context in item["contexts"]:
                row = db.execute(
                    "SELECT * FROM editorial_context WHERE id=?", (context,)
                ).fetchone()
                if row is None or not any(
                    r["asset"] == row["asset"]
                    and rational(r["in"]) <= rational(row["start"]) < rational(r["out"])
                    for r in validation["ranges"]
                ):
                    raise ValueError(
                        "deliverable context does not support its source excerpt"
                    )
    body = {"name": name, "brief": brief, "items": items}
    if len(json_text(body).encode()) > 1_000_000:
        raise ValueError("batch manifest exceeds 1 MB")
    with p.db() as db:
        db.execute(
            "INSERT INTO editorial_batches VALUES (?,?,?)",
            (name, json_text(body), "{}"),
        )
    return {
        "batch": name,
        "deliverables": len(items),
        "planHash": hashlib.sha256(json_text(body).encode()).hexdigest(),
        "status": "planned, not approved or exported",
    }


def batch_start(engine, project, name, preview=True, approved=False):
    p = engine.project(project)
    schema(p)
    if (
        type(preview) is not bool
        or type(approved) is not bool
        or not preview
        and not approved
    ):
        raise ValueError("final batch exports require explicit boolean user approval")
    with p.db() as db:
        row = db.execute(
            "SELECT body FROM editorial_batches WHERE id=?", (identifier(name),)
        ).fetchone()
    if row is None:
        raise ValueError("batch not found")
    return engine.jobs.submit(
        project,
        "deliverables",
        {
            "batch": name,
            "preview": preview,
            "approved": approved,
            "planHash": hashlib.sha256(row["body"].encode()).hexdigest(),
        },
    )


def batch_run(engine, project, args, job):
    p = engine.project(project)
    schema(p)
    with p.db() as db:
        row = db.execute(
            "SELECT * FROM editorial_batches WHERE id=?", (args["batch"],)
        ).fetchone()
    if (
        row is None
        or hashlib.sha256(row["body"].encode()).hexdigest() != args["planHash"]
    ):
        raise ValueError("approved batch manifest changed")
    body, state = json.loads(row["body"]), json.loads(row["state"])
    mode = "preview" if args["preview"] else "final"
    for index, item in enumerate(body["items"]):
        key = mode + ":" + item["name"]
        prior = state.get(key)
        if prior:
            path = engine.policy.read(prior["video"])
            if digest(path) != prior["videoHash"]:
                raise ValueError(
                    "successful batch output was modified; preserve and repair explicitly"
                )
            engine.revision(project, prior["revision"])
            validation = p.validate(item["plan"])
            for source in {r["asset"] for r in validation["ranges"]} | {
                r["asset"] for r in validation.get("audioTracks", [])
            }:
                p.asset(source, verify=True)
            continue
        child = job + "-" + str(index)
        revision = engine._apply(project, {"plan": item["plan"]}, child)
        result = engine._render(
            project,
            {
                "output": str(
                    p.root
                    / "exports"
                    / (args["batch"] + "-" + item["name"] + "-" + mode + ".mp4")
                ),
                "preview": args["preview"],
                "seconds": "15",
                "revision": revision["revision"],
                "replace": False,
            },
            child,
        )
        state[key] = {
            "video": result["video"],
            "videoHash": digest(Path(result["video"])),
            "revision": revision["revision"],
            "qcPath": result["qcPath"],
        }
        with p.db() as db:
            db.execute(
                "UPDATE editorial_batches SET state=? WHERE id=?",
                (json_text(state), args["batch"]),
            )
        engine.jobs.update(job, progress=(index + 1) / len(body["items"]))
    return {
        "batch": args["batch"],
        "mode": mode,
        "completed": len(body["items"]),
        "outputs": [
            {k: v for k, v in state[mode + ":" + item["name"]].items()}
            for item in body["items"]
        ],
        "scope": "mechanical QC; editorial quality still requires preview review",
    }
