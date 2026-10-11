"""Synthetic native v2 cross-app acceptance; no private footage or provider calls."""

import hashlib, json, subprocess, sys
from pathlib import Path

P = json.loads(Path("/harness/paths.json").read_text())
root = Path("/fixture/raw")
root.mkdir()
derived = Path("/fixture/projects")
config = Path("/fixture/config.json")
config.write_text(
    json.dumps(
        {
            "readRoots": [str(root)],
            "writeRoot": str(derived),
            "filmcraft": P["filmcraft"] + "/bin/filmcraft-cli",
            "soundcraft": P["soundcraft"] + "/bin/soundcraft-cli",
            "craftApplications": {
                "effectcraft": P["effectcraft"] + "/bin/effectcraft-cli"
            },
        }
    )
)
B = P["badwater-video"] + "/bin/badwater-video"


def cli(*args, wait=False):
    r = subprocess.run(
        [B, "--config", str(config), *(["--wait"] if wait else []), *args],
        capture_output=True,
        text=True,
        timeout=1000,
    )
    assert r.returncode == 0 and not r.stderr, (args, r.stdout, r.stderr)
    return json.loads(r.stdout)


raw = root / "game.mp4"
subprocess.run(
    [
        P["ffmpeg"] + "/bin/ffmpeg",
        "-nostdin",
        "-v",
        "error",
        "-f",
        "lavfi",
        "-i",
        "testsrc2=size=160x96:rate=12:duration=4",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:sample_rate=48000:duration=4",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-threads",
        "3",
        "-shortest",
        str(raw),
    ],
    check=True,
)
before = hashlib.sha256(raw.read_bytes()).hexdigest()
cli("project", "create", "game")
asset = cli("ingest", "game", str(raw), wait=True)["assets"][0]["asset"]
obs = cli(
    "evidence", "start", "game", asset, "--options", '{"transcribe":false}', wait=True
)
assert obs["wordCount"] == 0
data = cli(
    "evidence",
    "query",
    "game",
    asset,
    obs["cacheKey"],
    "--kind",
    "levels",
    "--end",
    "4",
)
assert data["entries"]
plan = {
    "version": 2,
    "output": {"width": 96, "height": 160, "fps": "12", "aspect": "3/5"},
    "clips": [
        {
            "asset": asset,
            "in": "0",
            "out": "4",
            "reason": "Setup, activity and result",
            "fit": "cover",
        }
    ],
    "audioTracks": [],
}


def render_case(name, plan):
    path = derived / "game" / (name + ".json")
    path.write_text(json.dumps(plan))
    cli("timeline", "validate", "game", str(path))
    r = cli("timeline", "apply", "game", str(path), wait=True)
    v = cli("preview", "game", "--out", name + ".mp4", "--seconds", "4", wait=True)
    assert v["qc"]["passed"]
    return {"revision": r, "preview": v}


simple = render_case("v2-simple", plan)
plan["audioTracks"] = [
    {
        "asset": asset,
        "in": "0",
        "out": "4",
        "at": "0",
        "role": "music",
        "gainDb": -18,
        "fadeIn": "1/4",
        "fadeOut": "1/4",
    }
]
mix = render_case("v2-mix", plan)
plan["captions"] = {
    "mode": "highlight",
    "words": [
        {"clip": 0, "in": "0", "out": "1", "text": "GAME"},
        {"clip": 0, "in": "1", "out": "2", "text": "TIME"},
    ],
    "size": 12,
}
plan["effects"] = [{"recipe": "title", "at": "2", "duration": "1", "text": "PLAY"}]
animation = render_case("v2-animated", plan)
provenance = json.loads(Path(animation["revision"]["provenance"]).read_text())
mixed_audio = provenance["audioMixes"][0]["path"]


def rms(t):
    import numpy as np

    raw = subprocess.check_output(
        [
            P["ffmpeg"] + "/bin/ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-ss",
            str(t),
            "-i",
            mixed_audio,
            "-t",
            "0.04",
            "-ac",
            "1",
            "-f",
            "f32le",
            "-",
        ]
    )
    return float(np.sqrt(np.mean(np.frombuffer(raw, dtype="<f4") ** 2)))


assert rms(0.5) < rms(3) * 0.4, "native music did not duck under word intervals"


def pixels(video, t):
    import numpy as np

    data = subprocess.check_output(
        [
            P["ffmpeg"] + "/bin/ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-ss",
            str(t),
            "-i",
            video,
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ]
    )
    return np.frombuffer(data, dtype="uint8").reshape(160, 96, 3).astype(float)


import numpy as np

base = pixels(simple["preview"]["video"], 0.5)
caption = pixels(animation["preview"]["video"], 0.5)
assert np.abs(base[:24, :24] - caption[:24, :24]).mean() < 12, (
    "alpha overlay obscures underlying corner"
)
assert np.abs(base[108:140] - caption[108:140]).mean() > 2, (
    "word caption is not visibly composited"
)
assert (
    np.abs(
        pixels(simple["preview"]["video"], 3.5)
        - pixels(animation["preview"]["video"], 3.5)
    ).mean()
    < 12
), "effect persists outside declared interval"
retime = {
    **plan,
    "audioTracks": [],
    "effects": [],
    "captions": {
        "mode": "pop",
        "words": [{"clip": 0, "in": "1", "out": "2", "text": "FAST"}],
    },
    "clips": [
        {
            "asset": asset,
            "in": "0",
            "out": "4",
            "speed": "2",
            "reason": "explicit native retime with mapped word caption",
            "fit": "cover",
        }
    ],
}
fast = render_case("v2-speed", retime)
layered = {
    **plan,
    "audioTracks": [],
    "effects": [],
    "captions": {},
    "clips": [
        {**plan["clips"][0], "destinationRect": ["0", "0", "1", "1/2"]},
        {
            "asset": asset,
            "in": "0",
            "out": "4",
            "at": "0",
            "track": 2,
            "sourceRect": ["1/4", "1/4", "1/2", "1/2"],
            "destinationRect": ["0", "1/2", "1", "1/2"],
            "reason": "facecam-like second source layer",
            "fit": "contain",
        },
    ],
}
facecam = render_case("v2-layered", layered)
cli("project", "privacy", "game", "--allow-remote", "true")
from mcp_client import MCP

m = MCP([B, "--config", str(config), "mcp"], "editorial-video")
items = []


def data(r):
    return r.get("structuredContent") or json.loads(
        "\n".join(x["text"] for x in r["content"] if x["type"] == "text")
    )


for n in range(15):
    lo = str(n / 5)
    hi = str((n + 1) / 5)
    # Exact rational strings, never float time coercion.
    from fractions import Fraction

    lo = str(Fraction(n, 5))
    hi = str(Fraction(n + 1, 5))
    m.tool(
        "frame_inspect",
        {"project": "game", "asset": asset, "seconds": lo, "share_with_model": True},
    )
    context = data(
        m.tool(
            "context_record",
            {
                "project": "game",
                "context": {
                    "asset": asset,
                    "in": lo,
                    "out": hi,
                    "kind": "moment",
                    "summary": "Synthetic sampled context " + str(n),
                    "frameSeconds": [lo],
                    "uncertainty": "not a genuine editorial-quality claim",
                },
            },
        )
    )["context"]
    item_plan = {
        "version": 1,
        "output": {"width": 160, "height": 96, "fps": "12", "aspect": "5/3"},
        "clips": [
            {
                "asset": asset,
                "in": lo,
                "out": hi,
                "reason": "Distinct synthetic range " + str(n),
            }
        ],
    }
    items.append(
        {
            "name": "short" + str(n),
            "title": "Synthetic distinct " + str(n),
            "plan": item_plan,
            "contexts": [context],
        }
    )
m.tool(
    "deliverables_plan",
    {
        "project": "game",
        "batch": "fifteen",
        "items": items,
        "brief": "Fifteen mechanically distinct excerpts; no genuine idea-quality claim",
    },
)
refused = m.call(
    "tools/call",
    {
        "name": "deliverables_run",
        "arguments": {
            "project": "game",
            "batch": "fifteen",
            "preview": False,
            "user_approved_final": False,
        },
    },
)
assert refused.get("isError"), refused
m.close()
blocker = derived / "game/exports/fifteen-short1-preview.mp4"
blocker.parent.mkdir(exist_ok=True)
blocker.write_bytes(b"preserved synthetic existing output")
r = subprocess.run(
    [B, "--config", str(config), "--wait", "deliverables", "run", "game", "fifteen"],
    capture_output=True,
    text=True,
    timeout=1000,
)
assert r.returncode != 0 and "File exists" in r.stderr, (r.stdout, r.stderr)
first = derived / "game/exports/fifteen-short0-preview.mp4"
first_hash = hashlib.sha256(first.read_bytes()).hexdigest()
assert blocker.read_bytes() == b"preserved synthetic existing output"
blocker.rename(blocker.with_suffix(".sentinel"))
finished = cli("deliverables", "run", "game", "fifteen", wait=True)
assert finished["completed"] == 15 and len(finished["outputs"]) == 15
assert hashlib.sha256(first.read_bytes()).hexdigest() == first_hash
cli("project", "privacy", "game", "--allow-remote", "false")
m = MCP([B, "--config", str(config), "mcp"], "editorial-revoked")
refused = m.call(
    "tools/call",
    {"name": "context_query", "arguments": {"project": "game", "asset": asset}},
)
assert refused.get("isError"), refused
m.close()
assert before == hashlib.sha256(raw.read_bytes()).hexdigest()
Path("/fixture/acceptance.json").write_text(
    json.dumps(
        {
            "sourceUnchanged": True,
            "evidence": obs,
            "simple": simple,
            "mix": mix,
            "animated": animation,
            "independentAlphaAndCaptionPixels": True,
            "independentNativeMusicDucking": True,
            "retiming": fast,
            "layeredFacecam": facecam,
            "fifteenDistinct": finished,
            "partialFailureFirstOutputPreserved": True,
            "approvalAndRevocation": True,
            "scope": "synthetic native v2/batch mechanics, not gameplay understanding or real idea quality",
        },
        indent=2,
    )
)
print(
    "PASS native v2 layout/retiming/layers, Sound mix, native Effect alpha/word pixels, Film reopening/render/QC, fifteen distinct outputs and resumable partial-failure/approval/privacy"
)
