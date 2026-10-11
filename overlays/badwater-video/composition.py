"""Plan-v2 compiler: native FilmCraft tracks/time maps and selected-cut SoundCraft mix."""

import json
import math
import re
from fractions import Fraction
from store import (
    TICKS,
    PIPELINE,
    rational,
    json_text,
    atomic_json,
    digest,
    publish,
    output_settings,
)
from native import NativeMCP
import editing


def number(value, low, high):
    if (
        type(value) not in (int, float)
        or not math.isfinite(value)
        or not low <= value <= high
    ):
        raise ValueError("expected a finite bounded number")
    return float(value)


def rectangle(value):
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(
            "rectangles are normalized [x,y,width,height] rational strings"
        )
    x, y, w, h = map(rational, value)
    if not 0 <= x < 1 or not 0 <= y < 1 or not 0 < w <= 1 - x or not 0 < h <= 1 - y:
        raise ValueError("rectangle is outside the image")
    return [str(x), str(y), str(w), str(h)]


def validate(p, plan):
    if (
        type(plan.get("version")) is not int
        or plan["version"] != 2
        or set(plan)
        - {
            "version",
            "output",
            "clips",
            "audioTracks",
            "captions",
            "effects",
            "constraints",
            "nativeCommands",
            "notes",
        }
    ):
        raise ValueError("unsupported composition version/fields")
    if len(json_text(plan).encode()) > 1_000_000:
        raise ValueError("composition exceeds 1 MB")
    # Reuse v1 output, source-identity and editorial-constraint validation, never weaken it.
    clips = plan.get("clips", [])
    if not isinstance(clips, list) or not 1 <= len(clips) <= 200:
        raise ValueError("composition requires 1..200 video clips")
    ranges, cursor, end = [], Fraction(0), Fraction(0)
    for clip in clips:
        if set(clip) - {
            "asset",
            "in",
            "out",
            "at",
            "track",
            "speed",
            "audio",
            "sourceRect",
            "destinationRect",
            "fit",
            "reason",
            "positionKeys",
        }:
            raise ValueError("unknown composition clip fields")
        asset = p.asset(clip["asset"])
        a, b = rational(clip["in"]), rational(clip["out"])
        speed = rational(clip.get("speed", "1"))
        if (
            not any(s["codec_type"] == "video" for s in asset["metadata"]["streams"])
            or not 0 <= a < b <= rational(asset["metadata"]["duration"])
            or not Fraction(1, 4) <= speed <= 4
        ):
            raise ValueError("invalid video source range or speed (1/4..4)")
        track = clip.get("track", 1)
        at = rational(clip.get("at", str(cursor)))
        if (
            type(track) is not int
            or not 1 <= track <= 8
            or at < 0
            or type(clip.get("audio", True)) is not bool
            or clip.get("fit", "contain") not in {"contain", "cover"}
        ):
            raise ValueError(
                "tracks 1..8, nonnegative placement, boolean audio and contain/cover fit required"
            )
        if (
            not isinstance(clip.get("reason"), str)
            or not 1 <= len(clip["reason"]) <= 1000
        ):
            raise ValueError("each clip needs a bounded editorial reason")
        duration = (b - a) / speed
        finish = at + duration
        if any(
            r["track"] == track
            and at < rational(r["timelineOut"])
            and finish > rational(r["timelineIn"])
            for r in ranges
        ):
            raise ValueError(
                "overlapping video clips on one track; use explicit layers"
            )
        source_rect = rectangle(clip.get("sourceRect", ["0", "0", "1", "1"]))
        destination = rectangle(clip.get("destinationRect", ["0", "0", "1", "1"]))
        keys = clip.get("positionKeys", [])
        if not isinstance(keys, list) or len(keys) > 100:
            raise ValueError("position keyframes exceed 100 per clip")
        previous = Fraction(-1)
        for key in keys:
            if (
                set(key) != {"at", "x", "y"}
                or not previous < rational(key["at"]) <= duration
            ):
                raise ValueError(
                    "position keys must be strictly increasing clip-relative times"
                )
            previous = rational(key["at"])
            number(key["x"], 0, 1)
            number(key["y"], 0, 1)
        ranges.append(
            {
                "asset": asset["id"],
                "in": str(a),
                "out": str(b),
                "timelineIn": str(at),
                "timelineOut": str(finish),
                "speed": str(speed),
                "track": track,
                "audio": clip.get("audio", True),
                "sourceRect": source_rect,
                "destinationRect": destination,
                "fit": clip.get("fit", "contain"),
                "positionKeys": keys,
                "reason": clip["reason"],
            }
        )
        end = max(end, finish)
        if track == 1:
            cursor = finish
    base = sorted(
        [r for r in ranges if r["track"] == 1], key=lambda r: rational(r["timelineIn"])
    )
    covered = Fraction(0)
    for r in base:
        if rational(r["timelineIn"]) != covered:
            raise ValueError("base video track must cover the output without gaps")
        covered = rational(r["timelineOut"])
    if not base or covered != end or end > 3600:
        raise ValueError(
            "base track must cover every overlay and duration must be <=1 hour"
        )
    output_settings(plan["output"])
    constraints = plan.get("constraints", {})
    if set(constraints) - {
        "targetDuration",
        "tolerance",
        "maxCutSeconds",
        "mustInclude",
        "mustExclude",
    }:
        raise ValueError("unknown editorial constraint")
    fps = rational(plan["output"]["fps"])
    tolerance = rational(constraints.get("tolerance", str(1 / fps)))
    if (
        tolerance < 0
        or "targetDuration" in constraints
        and abs(end - rational(constraints["targetDuration"])) > tolerance
    ):
        raise ValueError("composition does not meet target duration")
    if "maxCutSeconds" in constraints and any(
        rational(r["timelineOut"]) - rational(r["timelineIn"])
        > rational(constraints["maxCutSeconds"])
        for r in base
    ):
        raise ValueError("composition exceeds maximum shot duration")
    for mode in ["mustInclude", "mustExclude"]:
        for required in constraints.get(mode, []):
            asset = p.asset(required["asset"])
            a, b = rational(required["in"]), rational(required["out"])
            if not 0 <= a < b <= rational(asset["metadata"]["duration"]):
                raise ValueError("constraint source range is invalid")
            selected = sorted(
                (rational(r["in"]), rational(r["out"]))
                for r in ranges
                if r["asset"] == required["asset"]
            )
            if mode == "mustExclude" and any(x < b and y > a for x, y in selected):
                raise ValueError("composition includes an excluded source range")
            covered = a
            for x, y in selected:
                if x <= covered:
                    covered = max(covered, y)
            if mode == "mustInclude" and covered < b:
                raise ValueError("composition misses a required source range")
    audio = plan.get("audioTracks", [])
    if not isinstance(audio, list) or len(audio) > 100:
        raise ValueError("at most 100 explicit audio clips")
    audio_ranges = []
    for clip in audio:
        if set(clip) - {
            "asset",
            "in",
            "out",
            "at",
            "role",
            "stream",
            "gainDb",
            "fadeIn",
            "fadeOut",
            "duck",
            "beatAnchor",
            "cacheKey",
        }:
            raise ValueError("unknown audio fields")
        asset = p.asset(clip["asset"])
        a, b, at = rational(clip["in"]), rational(clip["out"]), rational(clip["at"])
        stream = clip.get("stream", 0)
        streams = [
            s for s in asset["metadata"]["streams"] if s["codec_type"] == "audio"
        ]
        if (
            type(stream) is not int
            or not 0 <= stream < len(streams)
            or not 0 <= a < b <= rational(asset["metadata"]["duration"])
            or not 0 <= at < end
            or at + b - a > end
        ):
            raise ValueError("invalid audio source/stream/placement")
        if clip.get("role") not in {"dialogue", "game", "music", "sfx"}:
            raise ValueError("audio role must be dialogue/game/music/sfx")
        number(clip.get("gainDb", 0), -60, 6)
        for key in ["fadeIn", "fadeOut"]:
            if not 0 <= rational(clip.get(key, "0")) <= min(Fraction(5), b - a):
                raise ValueError("fade must fit its clip and be <=5 seconds")
        duck = clip.get("duck", [])
        if not isinstance(duck, list) or len(duck) > 1000:
            raise ValueError("duck curve exceeds 1000 points")
        previous = Fraction(-1)
        for point in duck:
            if (
                set(point) != {"at", "db"}
                or not previous < rational(point["at"]) <= b - a
            ):
                raise ValueError("duck points require increasing relative times")
            previous = rational(point["at"])
            number(point["db"], -60, 0)
        if "beatAnchor" in clip:
            anchor = clip["beatAnchor"]
            if set(anchor) != {"source", "timeline", "tolerance"}:
                raise ValueError("beatAnchor requires source,timeline,tolerance")
            s, t, eps = map(
                rational, [anchor["source"], anchor["timeline"], anchor["tolerance"]]
            )
            if not a <= s < b or not 0 <= eps <= 1 or abs((at + s - a) - t) > eps:
                raise ValueError(
                    "music beat/punchline anchor is not aligned; move music rather than truncate speech"
                )
        audio_ranges.append(
            {**clip, "in": str(a), "out": str(b), "at": str(at), "stream": stream}
        )
    captions = plan.get("captions", {})
    if (
        set(captions)
        - {
            "words",
            "fromEvidence",
            "mode",
            "size",
            "anchor",
            "color",
            "highlight",
            "correctionsReviewed",
        }
        or captions.get("mode", "highlight") not in {"highlight", "reveal", "pop"}
        or type(captions.get("correctionsReviewed", False)) is not bool
    ):
        raise ValueError(
            "unknown caption style/mode or invalid correction authorization"
        )
    if captions.get("anchor", "bottom") not in {"top", "middle", "bottom"} or any(
        not isinstance(captions.get(k, default), str)
        or not re.fullmatch(
            r"#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?", captions.get(k, default)
        )
        for k, default in [("color", "#ffffff"), ("highlight", "#ffcc00")]
    ):
        raise ValueError(
            "caption colors must be hex RGB/RGBA and anchor top/middle/bottom"
        )
    words = captions.get("words", [])
    if "fromEvidence" in captions:
        import evidence

        reference = captions["fromEvidence"]
        if set(reference) != {"asset", "cacheKey"} or words:
            raise ValueError(
                "caption fromEvidence requires asset/cacheKey and excludes manual words"
            )

        class Reader:
            policy = p.policy
            config = p.policy.config

            def project(self, _):
                return p

        data = evidence.read(
            Reader(), p.name, reference["asset"], reference["cacheKey"]
        )
        words = []
        for i, r in enumerate(ranges):
            if r["asset"] != reference["asset"]:
                continue
            words.extend(
                {"clip": i, "in": w["start"], "out": w["end"], "text": w["text"]}
                for w in data["words"]
                if rational(r["in"])
                <= rational(w["start"])
                < rational(w["end"])
                <= rational(r["out"])
            )
    if not isinstance(words, list) or len(words) > 4000:
        raise ValueError("captions are bounded to 4000 words per deliverable")
    number(captions.get("size", max(12, plan["output"]["height"] // 24)), 8, 200)
    mapped = []
    for word in words:
        if (
            set(word) - {"clip", "in", "out", "text", "emphasis"}
            or type(word.get("clip")) is not int
            or not 0 <= word["clip"] < len(ranges)
            or not isinstance(word.get("text"), str)
            or not 1 <= len(word["text"].encode()) <= 160
            or type(word.get("emphasis", False)) is not bool
        ):
            raise ValueError(
                "caption words require clip index, source in/out and bounded text"
            )
        r = ranges[word["clip"]]
        a, b = rational(word["in"]), rational(word["out"])
        if not rational(r["in"]) <= a < b <= rational(r["out"]):
            raise ValueError("caption word is outside its source clip")
        speed = rational(r["speed"])
        start = rational(r["timelineIn"]) + (a - rational(r["in"])) / speed
        stop = start + (b - a) / speed
        mapped.append({**word, "at": str(start), "end": str(stop)})
    mapped.sort(key=lambda w: rational(w["at"]))
    if any(rational(b["at"]) < rational(a["end"]) for a, b in zip(mapped, mapped[1:])):
        raise ValueError("overlapping caption words; resolve speakers explicitly")
    effects = plan.get("effects", [])
    if not isinstance(effects, list) or len(effects) > 100:
        raise ValueError("at most 100 effect cues")
    for cue in effects:
        if (
            set(cue) - {"recipe", "at", "duration", "text", "strength"}
            or cue.get("recipe") not in {"title", "punchline", "callout"}
            or not isinstance(cue.get("text"), str)
            or not 1 <= len(cue["text"]) <= 200
            or not 0 <= rational(cue["at"]) < end
            or not 0
            < rational(cue["duration"])
            <= min(Fraction(10), end - rational(cue["at"]))
        ):
            raise ValueError("invalid bounded native effect cue")
        number(cue.get("strength", 1), 0.1, 2)
    editing.validate(plan.get("nativeCommands", []))
    return {
        "valid": True,
        "version": 2,
        "duration": str(end),
        "output": plan["output"],
        "ranges": ranges,
        "audio": {},
        "audioTracks": audio_ranges,
        "captionWords": mapped,
        "effects": effects,
        "semantics": "exact source-to-timeline mapping; explicit layers; native editors only",
    }


def film_command(film, name, params):
    return film.tool("command_run", {"id": name, "params": params})


def dependencies(p, revision):
    with p.db() as db:
        if not db.execute(
            "SELECT 1 FROM sqlite_master WHERE name='revision_dependencies'"
        ).fetchone():
            raise ValueError("v2 revision dependency receipt missing")
        row = db.execute(
            "SELECT hash FROM revision_dependencies WHERE revision=?", (revision,)
        ).fetchone()
    path = p.policy.read(p.root / "revisions" / str(revision) / "provenance.json")
    if (
        row is None
        or path.stat().st_size > 16 * 1024 * 1024
        or digest(path) != row["hash"]
    ):
        raise ValueError("v2 provenance/dependency receipt modified")
    body = json.loads(path.read_text())
    for item in body["effectAssets"] + body["audioMixes"]:
        for key, expected in [
            ("path", item["hash"]),
            ("nativeProject", item["nativeProjectHash"]),
        ]:
            source = p.policy.read(item[key])
            if not source.is_relative_to(p.root) or digest(source) != expected:
                raise ValueError(
                    "native derived effect/audio dependency changed; create an explicit new revision"
                )


def apply(engine, project, plan, job):
    import motion

    p = engine.project(project)
    val = validate(p, plan)
    sources = {
        r["asset"]: p.asset(r["asset"], verify=True)
        for r in [*val["ranges"], *val["audioTracks"]]
    }
    work = engine.policy.write(p.root / ".work" / job / "native.fcproj").parent
    for r in val["ranges"]:
        source = sources[r["asset"]]
        if not set(source["metadata"]["format"]["format_name"].split(",")) & {
            "mov",
            "mp4",
            "matroska",
            "webm",
        }:
            raise ValueError(
                "composition video sources require verified streaming containers"
            )
    overlays = (
        motion.render(engine, p, work, val, plan.get("captions", {}))
        if val["captionWords"] or val["effects"]
        else []
    )
    mixes = mix(engine, p, work, val, sources) if val["audioTracks"] else []
    with (
        (work / "film.stderr").open("w") as log,
        NativeMCP(
            engine.policy.sandbox([engine.config["filmcraft"], "mcp"], work), log
        ) as film,
    ):
        film_command(film, "file.newProject", {"name": project})
        settings = val["output"]
        film_command(
            film,
            "file.newSequence",
            {
                "name": project,
                "width": settings["width"],
                "height": settings["height"],
                "fps": float(rational(settings["fps"])),
                "video": max(r["track"] for r in val["ranges"]) + bool(overlays),
                "audio": 2,
            },
        )
        ids = {}
        clip_ids = []
        expected = []
        for r in val["ranges"]:
            if r["asset"] not in ids:
                ids[r["asset"]] = film_command(
                    film, "file.import", {"paths": [sources[r["asset"]]["path"]]}
                )["items"][0]
            result = film_command(
                film,
                "timeline.place",
                {
                    "item": ids[r["asset"]],
                    "track": f"V{r['track']}",
                    "audioTrack": "A1",
                    "time": round(rational(r["timelineIn"]) * TICKS),
                    "sourceIn": round(rational(r["in"]) * TICKS),
                    "duration": round((rational(r["out"]) - rational(r["in"])) * TICKS),
                    "video": True,
                    "audio": r["audio"],
                },
            )
            clip = result["clips"][0]
            clip_ids.append(clip)
            if r["speed"] != "1":
                film_command(
                    film,
                    "clip.speedDuration",
                    {
                        "clips": [clip],
                        "speed": float(rational(r["speed"]) * 100),
                        "reverse": False,
                        "ripple": False,
                        "interpolation": "frameSampling",
                    },
                )
            frame = next(
                s
                for s in sources[r["asset"]]["metadata"]["streams"]
                if s["codec_type"] == "video"
            )
            sw, sh = frame["width"], frame["height"]
            sx, sy, cw, ch = map(lambda x: float(rational(x)), r["sourceRect"])
            dx, dy, dw, dh = map(lambda x: float(rational(x)), r["destinationRect"])
            scale = (min if r["fit"] == "contain" else max)(
                dw * settings["width"] / (cw * sw), dh * settings["height"] / (ch * sh)
            )
            position = [
                (dx + dw / 2) * settings["width"] + (0.5 - sx - cw / 2) * sw * scale,
                (dy + dh / 2) * settings["height"] + (0.5 - sy - ch / 2) * sh * scale,
            ]
            for param, value in [("scale", scale * 100), ("position", position)]:
                film_command(
                    film,
                    "effects.setParam",
                    {"clip": clip, "effect": "motion", "param": param, "value": value},
                )
            if r["sourceRect"] != ["0", "0", "1", "1"]:
                film_command(film, "effects.apply", {"clips": [clip], "effect": "crop"})
                for param, value in [
                    ("left", sx * 100),
                    ("top", sy * 100),
                    ("right", (1 - sx - cw) * 100),
                    ("bottom", (1 - sy - ch) * 100),
                ]:
                    film_command(
                        film,
                        "effects.setParam",
                        {
                            "clip": clip,
                            "effect": "crop",
                            "param": param,
                            "value": value,
                        },
                    )
            for key in r["positionKeys"]:
                film_command(
                    film,
                    "effects.addKeyframe",
                    {
                        "clip": clip,
                        "effect": "motion",
                        "param": "position",
                        "mediaTime": round(
                            (
                                rational(r["in"])
                                + rational(key["at"]) * rational(r["speed"])
                            )
                            * TICKS
                        ),
                        "value": [
                            key["x"] * settings["width"],
                            key["y"] * settings["height"],
                        ],
                    },
                )
            expected.append((clip, r))
        for entry in overlays:
            item = film_command(film, "file.import", {"paths": [entry["path"]]})[
                "items"
            ][0]
            film_command(
                film,
                "timeline.place",
                {
                    "item": item,
                    "track": f"V{max(r['track'] for r in val['ranges']) + 1}",
                    "time": round(rational(entry["at"]) * TICKS),
                    "sourceIn": 0,
                    "duration": round(rational(entry["duration"]) * TICKS),
                    "video": True,
                    "audio": False,
                },
            )
        for entry in mixes:
            item = film_command(film, "file.import", {"paths": [entry["path"]]})[
                "items"
            ][0]
            film_command(
                film,
                "timeline.place",
                {
                    "item": item,
                    "track": "A2",
                    "time": round(rational(entry["at"]) * TICKS),
                    "sourceIn": 0,
                    "duration": round(rational(entry["duration"]) * TICKS),
                    "video": False,
                    "audio": True,
                },
            )
        native_results = editing.run(film, plan.get("nativeCommands", []), clip_ids)
        inspection = film.tool("sequence_inspect", {})
        native = work / "native.fcproj"
        film_command(film, "file.saveAs", {"path": str(native)})
        reopened = film_command(film, "file.open", {"path": str(native)})
        after = film.tool("sequence_inspect", {})
        atomic_json(work / "inspection-before.json", inspection)
        atomic_json(work / "inspection-after.json", after)
        # Selection/playhead are transient UI state, not saved editorial content.
        content = lambda value: {
            k: v for k, v in value.items() if k not in {"selection", "playhead"}
        }
        if reopened.get("missingMedia") or content(after) != content(inspection):
            raise ValueError(
                "native composition differs after save/reopen or has missing media"
            )
        actual = {c["clip"]: c for track in inspection["video"] for c in track["items"]}
        tolerance = round(TICKS / rational(settings["fps"]))
        for cid, r in expected:
            observed = actual.get(cid)
            if (
                observed is None
                or observed["item"] != ids[r["asset"]]
                or abs(observed["start"] - round(rational(r["timelineIn"]) * TICKS))
                > tolerance
                or abs(observed["end"] - round(rational(r["timelineOut"]) * TICKS))
                > tolerance
                or abs(observed["sourceIn"] - round(rational(r["in"]) * TICKS))
                > tolerance
                or abs(observed["sourceOut"] - round(rational(r["out"]) * TICKS))
                > tolerance
            ):
                raise ValueError("native v2 source/range/time map differs from plan")
    for asset in sources:
        p.asset(asset, verify=True)
    with p.db() as db:
        latest = db.execute("SELECT MAX(id) FROM revisions").fetchone()[0]
        revision = (latest or 0) + 1
        directory = engine.policy.write(
            p.root / "revisions" / str(revision) / "project.fcproj"
        ).parent
        target = directory / "project.fcproj"
        publish(native, target)
        atomic_json(directory / "plan.json", plan)
        atomic_json(
            directory / "provenance.json",
            {
                "pipeline": PIPELINE,
                "validation": val,
                "sources": {
                    k: {"path": v["path"], "hash": v["hash"]}
                    for k, v in sources.items()
                },
                "nativeInspection": inspection,
                "nativeCommandResults": native_results,
                "effectAssets": overlays,
                "audioMixes": mixes,
            },
        )
        db.execute(
            "CREATE TABLE IF NOT EXISTS revision_dependencies(revision INTEGER PRIMARY KEY, hash TEXT)"
        )
        db.execute(
            "INSERT INTO revision_dependencies VALUES (?,?)",
            (revision, digest(directory / "provenance.json")),
        )
        db.execute(
            "INSERT INTO revisions VALUES (?,?,?,?,?)",
            (revision, latest, json_text(plan), str(target), digest(target)),
        )
    return {
        "revision": revision,
        "parent": latest,
        "nativeProject": str(target),
        "plan": str(directory / "plan.json"),
        "provenance": str(directory / "provenance.json"),
        "duration": val["duration"],
        "originalsWritten": False,
    }


def duck_curve(clip, words):
    length = rational(clip["out"]) - rational(clip["in"])
    at = rational(clip["at"])
    explicit = clip.get("duck", [])
    intervals = []
    if clip["role"] == "music" and not explicit:
        for word in words:
            a = max(Fraction(0), rational(word["at"]) - at - Fraction(1, 10))
            b = min(length, rational(word["end"]) - at + Fraction(1, 5))
            if b > a:
                if intervals and a <= intervals[-1][1]:
                    intervals[-1] = (intervals[-1][0], max(intervals[-1][1], b))
                else:
                    intervals.append((a, b))
    points = {Fraction(0): 0, Fraction(length): 0}
    if explicit:
        points.update({rational(x["at"]): x["db"] for x in explicit})
    else:
        for a, b in intervals:
            points[max(Fraction(0), a - Fraction(1, 20))] = 0
            points[a] = -12
            points[b] = -12
            if b < length:
                points[min(length, b + Fraction(1, 10))] = 0
    fade_in, fade_out = (
        rational(clip.get("fadeIn", "0")),
        rational(clip.get("fadeOut", "0")),
    )
    base = sorted(points.items())
    times = set(points)
    if fade_in:
        times.add(fade_in)
    if fade_out:
        times.add(length - fade_out)
    curve = []
    for t in sorted(times):
        fade = -60 * float(1 - t / fade_in) if fade_in and t < fade_in else 0
        if fade_out and t > length - fade_out:
            fade += -60 * float((t - (length - fade_out)) / fade_out)
        curve.append((t, curve_at(base, t) + fade))
    return curve


def curve_at(points, t):
    for (a, x), (b, y) in zip(points, points[1:]):
        if a <= t <= b:
            return float(x + (y - x) * float((t - a) / (b - a))) if b > a else y
    return points[0][1] if t < points[0][0] else points[-1][1]


def mix(engine, p, work, val, sources):
    """Native stereo mix in <=120s windows, never whole-recording native audio imports."""
    result = []
    duration = rational(val["duration"])
    for window in range(math.ceil(duration / 120)):
        start = Fraction(window * 120)
        stop = min(duration, start + 120)
        folder = engine.policy.write(work / f"mix-{window}" / "session.scraft").parent
        with (
            (folder / "native.stderr").open("w") as log,
            NativeMCP(
                engine.policy.sandbox([engine.config["soundcraft"], "mcp"], folder), log
            ) as sound,
        ):
            sound.tool("new_session", {"name": f"mix-{window}"})
            for n, clip in enumerate(val["audioTracks"]):
                at = rational(clip["at"])
                end = at + rational(clip["out"]) - rational(clip["in"])
                lo = max(start, at)
                hi = min(stop, end)
                if hi <= lo:
                    continue
                source = sources[clip["asset"]]
                source_in = rational(clip["in"]) + lo - at
                wav = folder / f"cut-{n}.wav"
                engine.policy.run(
                    [
                        engine.config["ffmpeg"],
                        "-nostdin",
                        "-v",
                        "error",
                        "-ss",
                        str(float(source_in)),
                        "-i",
                        source["path"],
                        "-t",
                        str(float(hi - lo)),
                        "-map",
                        f"0:a:{clip['stream']}",
                        "-vn",
                        "-ac",
                        "2",
                        "-ar",
                        "48000",
                        "-c:a",
                        "pcm_s16le",
                        str(wav),
                    ]
                )
                imported = sound.tool(
                    "import_audio",
                    {
                        "path": str(wav),
                        "at": {"seconds": float(lo - start)},
                        "new_tracks": True,
                    },
                )
                ids = [entry["clip"] for entry in imported["imported"]]
                sound.tool(
                    "execute",
                    {
                        "command": "clip.gain",
                        "params": {"clips": ids, "db": clip.get("gainDb", 0)},
                    },
                )
                session = sound.tool("inspect_session", {})
                atomic_json(folder / f"inspect-{n}.json", session)
                atomic_json(folder / f"import-{n}.json", imported)
                track = imported["imported"][0]["track"]
                points = duck_curve(clip, val["captionWords"])
                selected = {
                    lo: curve_at(points, lo - at),
                    hi: curve_at(points, hi - at),
                }
                selected.update(
                    {at + t: value for t, value in points if lo <= at + t <= hi}
                )
                for t, value in sorted(selected.items()):
                    sound.tool(
                        "execute",
                        {
                            "command": "automation.set_point",
                            "params": {
                                "track": track,
                                "param": "volume",
                                "at": {"seconds": float(t - start)},
                                "value": value,
                            },
                        },
                    )
            measurement = sound.tool(
                "bounce_mix",
                {
                    "path": str(folder / "measure.wav"),
                    "start": {"seconds": 0},
                    "end": {"seconds": float(stop - start)},
                    "bit_depth": "24",
                },
            )
            peak = measurement.get("true_peak_db")
            attenuation = (
                min(0, -1 - float(peak))
                if isinstance(peak, (int, float)) and math.isfinite(peak)
                else 0
            )
            if attenuation:
                tracks = [
                    t["id"]
                    for t in sound.tool("inspect_session", {})["tracks"]
                    if t["kind"] == "audio"
                ]
                sound.tool(
                    "execute",
                    {
                        "command": "mix.volume",
                        "params": {"tracks": tracks, "delta_db": attenuation},
                    },
                )
            native = folder / "session.scraft"
            sound.tool("save_session", {"path": str(native)})
            before = sound.tool("inspect_session", {})
            reopened = sound.tool("open_session", {"path": str(native)})
            after = sound.tool("inspect_session", {})
            if reopened.get("missing") or before["tracks"] != after["tracks"]:
                raise ValueError(
                    "native mixed audio/automation differs after save/reopen"
                )
            path = folder / "mix.wav"
            report = sound.tool(
                "bounce_mix",
                {
                    "path": str(path),
                    "start": {"seconds": 0},
                    "end": {"seconds": float(stop - start)},
                    "bit_depth": "24",
                },
            )
        result.append(
            {
                "path": str(path),
                "hash": digest(path),
                "at": str(start),
                "duration": str(stop - start),
                "nativeProject": str(native),
                "nativeProjectHash": digest(native),
                "report": report,
                "peakAttenuationDb": attenuation,
            }
        )
    return result
