"""Streaming local audio/visual evidence. Scores propose inspection, never certify meaning."""

import hashlib
import json
import math
import re
from fractions import Fraction
from pathlib import Path

import numpy as np
from store import atomic_json, digest, json_text, rational

PROFILES = {"gameplay", "streamer", "podcast", "instructional", "music"}


def seconds(value):
    return str(Fraction(round(float(value) * 1000), 1000))


def options(value):
    defaults = {
        "profile": "gameplay",
        "audioStream": 0,
        "transcribe": True,
        "visual": True,
    }
    if not isinstance(value, dict) or set(value) - set(defaults):
        raise ValueError("unknown evidence options")
    out = {**defaults, **value}
    if (
        out["profile"] not in PROFILES
        or type(out["audioStream"]) is not int
        or not 0 <= out["audioStream"] <= 31
        or any(type(out[k]) is not bool for k in ["transcribe", "visual"])
    ):
        raise ValueError(
            "evidence requires a profile, audioStream integer 0..31 and literal boolean flags"
        )
    return out


def token_words(segments, offset, duration):
    """Merge subword tokens; keep estimated times/probabilities, not calibrated confidence."""
    words = []
    for segment in segments:
        if re.fullmatch(r"\s*(?:\[[^\]]*\]|\([^)]*\))\s*", segment.get("text", "")):
            continue
        current = None
        for token in segment.get("tokens", []):
            text = token.get("text", "")
            if (
                not text
                or text.startswith("[_")
                or text.startswith("<|")
                or not token.get("offsets")
            ):
                continue
            a = Fraction(offset) + Fraction(token["offsets"]["from"], 1000)
            b = min(duration, Fraction(offset) + Fraction(token["offsets"]["to"], 1000))
            if not 0 <= a < b <= duration:
                continue
            p = token.get("p")
            probability = (
                float(p)
                if isinstance(p, (int, float)) and math.isfinite(p) and 0 <= p <= 1
                else None
            )
            if current and not text[:1].isspace():
                current["text"] += text
                current["end"] = str(b)
                if probability is not None:
                    current["probability"] = min(
                        current.get("probability") or probability, probability
                    )
            else:
                current = {
                    "start": str(a),
                    "end": str(b),
                    "text": text.strip(),
                    "probability": probability,
                }
                words.append(current)
    return words


def audio_features(samples, start, rate=16000):
    """32-ms spectral onsets, half-second levels; bounded to one 30-second window."""
    samples = np.asarray(samples, dtype=np.float32)
    if not np.isfinite(samples).all():
        raise ValueError("non-finite decoded audio")
    levels, onsets = [], []
    for i in range(0, len(samples), rate // 2):
        block = samples[i : i + rate // 2]
        if not len(block):
            continue
        rms = float(np.sqrt(np.mean(block.astype(np.float64) ** 2)))
        peak = float(np.max(np.abs(block)))
        levels.append(
            {
                "seconds": seconds(start + i / rate),
                "rmsDb": round(20 * math.log10(max(rms, 1e-9)), 2),
                "peakDb": round(20 * math.log10(max(peak, 1e-9)), 2),
            }
        )
    previous = None
    flux = []
    for i in range(0, max(0, len(samples) - 1024), 512):
        spectrum = np.abs(np.fft.rfft(samples[i : i + 1024] * np.hanning(1024)))
        change = (
            float(np.maximum(spectrum - previous, 0).mean())
            if previous is not None
            else 0
        )
        flux.append((start + i / rate, change))
        previous = spectrum
    values = np.array([x[1] for x in flux])
    threshold = (
        float(np.median(values) + 3 * np.median(np.abs(values - np.median(values))))
        if len(values)
        else 0
    )
    for i in range(1, len(flux) - 1):
        t, x = flux[i]
        if (
            x > max(threshold, 0.02)
            and x >= flux[i - 1][1]
            and x > flux[i + 1][1]
            and (not onsets or t - float(rational(onsets[-1]["seconds"])) >= 0.20)
        ):
            onsets.append({"seconds": seconds(t), "strength": round(x, 4)})
    return levels, onsets


def music_grid(onsets):
    times = [float(rational(x["seconds"])) for x in onsets]
    intervals = [b - a for a, b in zip(times, times[1:]) if 0.25 <= b - a <= 1.2]
    if len(intervals) < 3:
        return {
            "bpmEstimate": None,
            "confidence": 0,
            "beats": [],
            "interpretation": "insufficient periodic onsets; supply manual anchors",
        }
    bins = {}
    for interval in intervals:
        bpm = 60 / interval
        while bpm < 60:
            bpm *= 2
        while bpm > 180:
            bpm /= 2
        key = round(bpm / 2) * 2
        bins[key] = bins.get(key, 0) + 1
    bpm = max(bins, key=bins.get)
    confidence = bins[bpm] / len(intervals)
    return {
        "bpmEstimate": bpm,
        "confidence": round(confidence, 3),
        "beats": [
            {"seconds": x["seconds"], "kind": "onset", "strength": x["strength"]}
            for x in onsets
        ],
        "interpretation": "onset/tempo candidates, not certified downbeats; variable tempo and offbeats require review",
    }


def schema(p):
    with p.db() as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS editorial_evidence(asset TEXT, cache_key TEXT, path TEXT, hash TEXT, PRIMARY KEY(asset,cache_key))"
        )


def start(engine, project, asset, value):
    p = engine.project(project)
    a = p.asset(asset)
    opt = options(value)
    if not 0 < rational(a["metadata"]["duration"]) <= 14400:
        raise ValueError("evidence is bounded to four hours per asset")
    key = hashlib.sha256(
        json_text(
            {
                "pipeline": engine.config["pipelineHash"],
                "model": engine.config["modelHash"],
                "options": opt,
            }
        ).encode()
    ).hexdigest()
    return {
        **engine.jobs.submit(
            project, "evidence", {"asset": asset, "options": opt, "cacheKey": key}
        ),
        "cacheKey": key,
    }


def run(engine, project, args, job):
    p = engine.project(project)
    a = p.asset(args["asset"], verify=True)
    opt = args["options"]
    duration = rational(a["metadata"]["duration"])
    streams = [s for s in a["metadata"]["streams"] if s["codec_type"] == "audio"]
    if streams and opt["audioStream"] >= len(streams):
        raise ValueError("selected audio stream is absent")
    root = engine.policy.write(
        p.root / "evidence" / a["id"] / args["cacheKey"] / job / "observations.json"
    ).parent
    words, segments, levels, onsets, motion = [], [], [], [], []
    if (
        opt["transcribe"]
        and streams
        and digest(Path(engine.config["model"])) != engine.config["modelHash"]
    ):
        raise ValueError("Whisper model content differs from its pinned SHA-256")
    count = math.ceil(duration / 28)
    for n in range(count):
        t = n * 28
        length = min(Fraction(30), duration - t)
        if streams:
            raw, _ = engine.policy.run(
                [
                    engine.config["ffmpeg"],
                    "-nostdin",
                    "-v",
                    "error",
                    "-ss",
                    str(t),
                    "-i",
                    a["path"],
                    "-t",
                    str(float(length)),
                    "-map",
                    f"0:a:{opt['audioStream']}",
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-f",
                    "f32le",
                    "-",
                ]
            )
            lv, ons = audio_features(np.frombuffer(raw, dtype="<f4"), t)
            levels.extend(
                x
                for x in lv
                if float(rational(x["seconds"])) < t + 28 or n == count - 1
            )
            onsets.extend(
                x
                for x in ons
                if float(rational(x["seconds"])) < t + 28 or n == count - 1
            )
            samples = np.frombuffer(raw, dtype="<f4")
            blocks = [
                i
                for i in range(0, len(samples), 320)
                if float(np.sqrt(np.mean(samples[i : i + 320].astype(np.float64) ** 2)))
                > 0.003
            ]
            if opt["transcribe"] and blocks:
                # Trim clear leading/trailing silence with 250ms context, not speaker/semantic VAD.
                lead = max(0, blocks[0] / 16000 - 0.25)
                tail = min(float(length), (blocks[-1] + 320) / 16000 + 0.25)
                speech_offset = Fraction(t) + Fraction(round(lead * 1000), 1000)
                speech_length = tail - lead
                wav = root / f"speech-{n:04d}.wav"
                prefix = root / f"speech-{n:04d}"
                engine.policy.run(
                    [
                        engine.config["ffmpeg"],
                        "-nostdin",
                        "-v",
                        "error",
                        "-ss",
                        str(float(speech_offset)),
                        "-i",
                        a["path"],
                        "-t",
                        str(speech_length),
                        "-map",
                        f"0:a:{opt['audioStream']}",
                        "-vn",
                        "-ac",
                        "1",
                        "-ar",
                        "16000",
                        "-c:a",
                        "pcm_s16le",
                        str(wav),
                    ]
                )
                engine.policy.run(
                    [
                        engine.config["whisper"],
                        "-m",
                        engine.config["model"],
                        "-f",
                        str(wav),
                        "-l",
                        "en",
                        "-t",
                        "3",
                        "-ng",
                        "-ojf",
                        "-of",
                        str(prefix),
                    ],
                    timeout=180,
                )
                body = json.loads(prefix.with_suffix(".json").read_text())
                incoming = token_words(body["transcription"], speech_offset, duration)
                for word in incoming:
                    # Overlap ownership belongs to the window whose core contains the word's midpoint.
                    midpoint = (rational(word["start"]) + rational(word["end"])) / 2
                    if (
                        t <= midpoint < min(duration, t + 28)
                        or n == count - 1
                        and midpoint >= t
                    ):
                        if words and rational(word["start"]) < rational(
                            words[-1]["end"]
                        ):
                            if word["text"].casefold().strip(".,!?") == words[-1][
                                "text"
                            ].casefold().strip(".,!?") or rational(
                                word["end"]
                            ) <= rational(words[-1]["end"]):
                                continue
                            word["asrStart"] = word["start"]
                            word["start"] = words[-1]["end"]
                            word["alignmentAdjusted"] = True
                        word["speaker"] = f"audio-track-{opt['audioStream']}"
                        word["id"] = len(words)
                        words.append(word)
                for s in body["transcription"]:
                    if re.fullmatch(
                        r"\s*(?:\[[^\]]*\]|\([^)]*\))\s*", s.get("text", "")
                    ):
                        continue
                    begin = speech_offset + Fraction(s["offsets"]["from"], 1000)
                    end = min(
                        duration, speech_offset + Fraction(s["offsets"]["to"], 1000)
                    )
                    if begin < end and begin < t + 28:
                        segments.append(
                            {
                                "start": str(begin),
                                "end": str(end),
                                "text": s["text"][:4000],
                            }
                        )
        if opt["visual"] and any(
            s["codec_type"] == "video" for s in a["metadata"]["streams"]
        ):
            raw, _ = engine.policy.run(
                [
                    engine.config["ffmpeg"],
                    "-nostdin",
                    "-v",
                    "error",
                    "-ss",
                    str(t),
                    "-i",
                    a["path"],
                    "-t",
                    str(float(length)),
                    "-an",
                    "-vf",
                    "fps=2,scale=32:18",
                    "-pix_fmt",
                    "rgb24",
                    "-f",
                    "rawvideo",
                    "-",
                ]
            )
            frames = (
                np.frombuffer(raw, dtype=np.uint8)
                .reshape(-1, 18, 32, 3)
                .astype(np.float32)
            )
            for i in range(1, min(len(frames), 56)):
                # Whole-image and HUD-edge change: evidence only; no kill/hero recognition claim.
                delta = np.abs(frames[i] - frames[i - 1]) / 255
                motion.append(
                    {
                        "seconds": seconds(t + i / 2),
                        "change": round(float(delta.mean()), 4),
                        "hudChange": round(
                            float(
                                np.concatenate(
                                    (delta[:4].ravel(), delta[-4:].ravel())
                                ).mean()
                            ),
                            4,
                        ),
                    }
                )
        engine.jobs.update(job, progress=(n + 1) / count * 0.9)
        if len(words) > 100000:
            raise ValueError("word evidence exceeds 100000 words; split the recording")
    candidates = []
    active = [float(rational(x["seconds"])) for x in levels if x["rmsDb"] > -22] + [
        float(rational(x["seconds"]))
        for x in motion
        if x["change"] > 0.14 or x["hudChange"] > 0.18
    ]
    for t in sorted(active):
        if (
            candidates
            and t <= float(rational(candidates[-1]["eventEnd"])) + 3
            and t - float(rational(candidates[-1]["in"])) < 90
        ):
            candidates[-1]["eventEnd"] = seconds(t)
            candidates[-1]["out"] = seconds(min(float(duration), t + 5))
        else:
            candidates.append(
                {
                    "id": f"moment-{len(candidates)}",
                    "asset": a["id"],
                    "in": seconds(max(0, t - 8)),
                    "out": seconds(min(float(duration), t + 5)),
                    "eventEnd": seconds(t),
                    "kind": "unclassified audiovisual activity",
                    "status": "needs-context-review",
                }
            )
    if opt["profile"] in {"podcast", "streamer", "instructional"}:
        chunk = []
        for word in words:
            chunk.append(word)
            if word["text"].endswith((".", "?", "!")) or len(chunk) >= 80:
                if len(chunk) >= 6:
                    candidates.append(
                        {
                            "id": f"speech-{chunk[0]['id']}",
                            "asset": a["id"],
                            "in": seconds(
                                max(0, float(rational(chunk[0]["start"])) - 2)
                            ),
                            "out": seconds(
                                min(
                                    float(duration),
                                    float(rational(chunk[-1]["end"])) + 2,
                                )
                            ),
                            "firstWordId": chunk[0]["id"],
                            "lastWordId": chunk[-1]["id"],
                            "kind": "unreviewed spoken idea/turn",
                            "status": "needs-qualifier-setup-payoff-review",
                        }
                    )
                chunk = []
    grid = music_grid(onsets)
    sections = []
    previous = None
    for window in range(math.ceil(duration / 30)):
        block = [
            x["rmsDb"]
            for x in levels
            if window * 30 <= float(rational(x["seconds"])) < (window + 1) * 30
        ]
        if block:
            energy = float(np.median(block))
            if previous is not None and abs(energy - previous) >= 6:
                sections.append(
                    {
                        "seconds": str(window * 30),
                        "kind": "energy section-change candidate",
                        "deltaDb": round(energy - previous, 2),
                    }
                )
            previous = energy
    grid["sections"] = sections
    result = {
        "version": 1,
        "asset": a["id"],
        "sourceHash": a["hash"],
        "cacheKey": args["cacheKey"],
        "pipelineHash": engine.config["pipelineHash"],
        "modelHash": engine.config["modelHash"],
        "options": opt,
        "words": words,
        "segments": segments,
        "levels": levels,
        "onsets": onsets,
        "motion": motion,
        "music": grid,
        "candidates": sorted(candidates, key=lambda c: rational(c["in"]))[:2000],
        "candidateTruncated": len(candidates) > 2000,
        "coverage": {
            "duration": str(duration),
            "audioStream": opt["audioStream"],
            "localVisualFps": 2 if motion else 0,
            "complete": True,
        },
        "uncertainty": "English ASR/token timing estimates and signal heuristics; not speaker identity, emotion, semantic game-event recognition or continuous model viewing",
    }
    if len(json_text(result).encode()) > 16 * 1024 * 1024:
        raise ValueError("evidence exceeds 16 MiB; split the recording")
    atomic_json(root / "observations.json", result)
    p.asset(a["id"], verify=True)
    schema(p)
    with p.db() as db:
        db.execute(
            "INSERT OR REPLACE INTO editorial_evidence VALUES (?,?,?,?)",
            (
                a["id"],
                args["cacheKey"],
                str(root / "observations.json"),
                digest(root / "observations.json"),
            ),
        )
        db.execute(
            "DELETE FROM transcript WHERE asset=? AND cache_key=?",
            (a["id"], args["cacheKey"]),
        )
        for segment in segments:
            db.execute(
                "INSERT INTO transcript VALUES (?,?,?,?,?)",
                (
                    a["id"],
                    args["cacheKey"],
                    segment["start"],
                    segment["end"],
                    segment["text"],
                ),
            )
    return {
        "asset": a["id"],
        "cacheKey": args["cacheKey"],
        "wordCount": len(words),
        "candidateCount": len(candidates),
        "path": str(root / "observations.json"),
        "modelSharing": False,
    }


def read(engine, project, asset, key):
    p = engine.project(project)
    p.asset(asset)
    schema(p)
    with p.db() as db:
        row = db.execute(
            "SELECT * FROM editorial_evidence WHERE asset=? AND cache_key=?",
            (asset, key),
        ).fetchone()
    if row is None:
        raise ValueError("evidence missing; analyze this source first")
    path = engine.policy.read(row["path"])
    if (
        not path.is_relative_to(p.root / "evidence")
        or path.stat().st_size > 16 * 1024 * 1024
        or digest(path) != row["hash"]
    ):
        raise ValueError("evidence cache modified or exceeds its bound; analyze again")
    data = json.loads(path.read_text())
    if (
        data["sourceHash"] != asset
        or data.get("pipelineHash") != engine.config["pipelineHash"]
        or data.get("modelHash") != engine.config["modelHash"]
    ):
        raise ValueError(
            "evidence source/model/pipeline identity differs; analyze again"
        )
    return data


def query(
    engine,
    project,
    asset,
    key,
    kind="words",
    start="0",
    end="30",
    offset=0,
    limit=20,
    local=False,
):
    if (
        kind
        not in {
            "words",
            "segments",
            "levels",
            "onsets",
            "motion",
            "candidates",
            "beats",
            "sections",
        }
        or type(offset) is not int
        or offset < 0
        or type(limit) is not int
        or not 1 <= limit <= 100
    ):
        raise ValueError(
            "evidence pages require a known kind, limit 1..100 and nonnegative offset"
        )
    a, b = rational(start), rational(end)
    if not 0 <= a < b or b - a > 120:
        raise ValueError("evidence windows are bounded to 120 seconds")
    p = engine.project(project)
    data = read(engine, project, asset, key)
    if kind in {"words", "segments"} and not local and not p.summary()["remoteConsent"]:
        raise ValueError(
            "transcript context requires explicit model-sharing permission"
        )
    values = data["music"][kind] if kind in {"beats", "sections"} else data[kind]
    selected = [
        x
        for x in values
        if rational(x.get("end", x.get("out", x.get("seconds", "0")))) >= a
        and rational(x.get("start", x.get("in", x.get("seconds", "0")))) < b
    ]
    page = selected[offset : offset + limit]
    if len(json_text(page).encode()) > 8000:
        raise ValueError("evidence page exceeds 8 KiB; request fewer entries")
    return {
        "asset": asset,
        "cacheKey": key,
        "kind": kind,
        "entries": page,
        "total": len(selected),
        "nextOffset": offset + len(page)
        if offset + len(page) < len(selected)
        else None,
        "musicEstimate": {
            k: v for k, v in data["music"].items() if k not in {"beats", "sections"}
        },
        "uncertainty": data["uncertainty"],
    }
