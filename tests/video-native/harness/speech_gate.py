"""Public synthetic speech spanning an overlapping analysis window; two immutable CPU models."""

import json, subprocess, hashlib, time, os, sys
from pathlib import Path
from fractions import Fraction
from mcp_client import MCP

P = json.loads(Path("/harness/paths.json").read_text())
B = P["badwater-video"] + "/bin/badwater-video"
raw = Path("/fixture/raw")
raw.mkdir()
projects = Path("/fixture/projects")
speech = raw / "voice.wav"
phrase = "Remember, do not rush forward until your team is ready. Hold the high ground and wait for your friends. Then protect the objective and finish the fight together."
subprocess.run(
    [P["espeak-ng"] + "/bin/espeak-ng", "-s", "130", "-w", str(speech), phrase],
    check=True,
)
media = raw / "streams.mkv"
subprocess.run(
    [
        P["ffmpeg"] + "/bin/ffmpeg",
        "-nostdin",
        "-v",
        "error",
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:s=160x96:r=12:d=45",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=220:sample_rate=48000:duration=45",
        "-i",
        str(speech),
        "-filter_complex",
        "[2:a]adelay=25500:all=1,apad[a]",
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-map",
        "[a]",
        "-t",
        "45",
        "-c:v",
        "libx264",
        "-c:a",
        "pcm_s16le",
        "-threads",
        "3",
        str(media),
    ],
    check=True,
)
before = hashlib.sha256(media.read_bytes()).hexdigest()
results = {}


def cli(config, *args, wait=False):
    r = subprocess.run(
        [B, "--config", str(config), *(["--wait"] if wait else []), *args],
        capture_output=True,
        text=True,
        timeout=1000,
    )
    assert r.returncode == 0 and not r.stderr, (args, r.stdout, r.stderr)
    return json.loads(r.stdout)


for name, model, h in [
    ("tiny.en", None, None),
    (
        "small.en",
        P["whisper-small-model"],
        "c6138d6d58ecc8322097e0f987c32f1be8bb0a18532a3f88f734d1bbf9c41e5d",
    ),
]:
    config = Path("/fixture/" + name + ".json")
    cfg = {
        "readRoots": [str(raw)],
        "writeRoot": str(projects),
        "asrModel": name,
        "filmcraft": P["filmcraft"] + "/bin/filmcraft-cli",
        "soundcraft": P["soundcraft"] + "/bin/soundcraft-cli",
        "craftApplications": {"effectcraft": P["effectcraft"] + "/bin/effectcraft-cli"},
    }
    if model:
        cfg.update(model=model, modelHash=h)
    config.write_text(json.dumps(cfg))
    project = name.replace(".", "-")
    cli(config, "project", "create", project)
    asset = cli(config, "ingest", project, str(media), wait=True)["assets"][0]["asset"]
    t = time.monotonic()
    job = cli(
        config,
        "evidence",
        "start",
        project,
        asset,
        "--options",
        '{"profile":"podcast","audioStream":1,"visual":false}',
        wait=True,
    )
    data = json.loads(Path(job["path"]).read_text())
    assert data["words"] and len(data["words"]) >= 15
    assert all(
        Fraction("25") <= Fraction(w["start"]) < Fraction(w["end"]) <= 45
        for w in data["words"]
    )
    assert any(
        Fraction(w["start"]) < 28 < Fraction(w["end"])
        or 28 <= Fraction(w["start"]) <= 30
        for w in data["words"]
    )
    results[name] = {
        "elapsedSeconds": time.monotonic() - t,
        "words": data["words"],
        "cacheKey": job["cacheKey"],
        "asset": asset,
        "configuration": cfg,
        "scope": "clear espeak synthetic speech, not a noisy-gameplay accuracy benchmark",
    }
    m = MCP([B, "--config", str(config), "mcp"], "speech-" + project)
    refused = m.call(
        "tools/call",
        {
            "name": "evidence_query",
            "arguments": {
                "project": project,
                "asset": asset,
                "cache_key": job["cacheKey"],
                "kind": "words",
                "start": "25",
                "end": "45",
            },
        },
    )
    assert refused.get("isError"), refused
    plan = {
        "version": 2,
        "output": {"width": 160, "height": 96, "fps": "12", "aspect": "5/3"},
        "clips": [
            {
                "asset": asset,
                "in": "25",
                "out": "45",
                "reason": "Preserve the complete synthetic statement",
            }
        ],
        "captions": {
            "fromEvidence": {"asset": asset, "cacheKey": job["cacheKey"]},
            "mode": "pop",
        },
    }
    result = m.tool("timeline_validate", {"project": project, "plan": plan})
    body = result.get("structuredContent") or json.loads(
        "\n".join(x["text"] for x in result["content"] if x["type"] == "text")
    )
    assert body["captionWords"] and all("text" not in w for w in body["captionWords"])
    m.close()
    cli(config, "project", "privacy", project, "--allow-remote", "true")
    found = cli(config, "search", project, "team")
    assert found["matches"], found
    cli(config, "project", "privacy", project, "--allow-remote", "false")
assert before == hashlib.sha256(media.read_bytes()).hexdigest()
Path("/fixture/acceptance.json").write_text(
    json.dumps(
        {
            "models": results,
            "separateStreamSelected": True,
            "overlapBoundarySpeech": True,
            "noTranscriptOrAutoCaptionTextWithoutConsent": True,
            "sourceUnchanged": True,
        },
        indent=2,
    )
)
print(
    "PASS selected speech stream, overlapping-window token timing for tiny.en/small.en, transcript indexing and consent-safe auto captions"
)
