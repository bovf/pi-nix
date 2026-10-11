"""Native generated asset promotion, reuse and identity/confinement negatives."""

import hashlib, json, subprocess
from pathlib import Path

P = json.loads(Path("/harness/paths.json").read_text())
raw = Path("/fixture/raw")
raw.mkdir()
projects = Path("/fixture/projects")
cfg = Path("/fixture/config.json")
cfg.write_text(
    json.dumps(
        {
            "readRoots": [str(raw)],
            "writeRoot": str(projects),
            "filmcraft": P["filmcraft"] + "/bin/filmcraft-cli",
            "soundcraft": P["soundcraft"] + "/bin/soundcraft-cli",
            "craftLauncher": P["badwater-craft-mcp"] + "/bin/badwater-craft-mcp",
            "craftApplications": {
                "effectcraft": P["effectcraft"] + "/bin/effectcraft-cli"
            },
        }
    )
)
B = P["badwater-video"] + "/bin/badwater-video"


def cli(*args, wait=False, success=True):
    r = subprocess.run(
        [B, "--config", str(cfg), *(["--wait"] if wait else []), *args],
        capture_output=True,
        text=True,
        timeout=1000,
    )
    if success:
        assert r.returncode == 0 and not r.stderr, (args, r.stdout, r.stderr)
        return json.loads(r.stdout)
    assert r.returncode != 0
    return r.stderr


cli("project", "create", "reuse")
cli("project", "create", "other")
source = raw / "red.mp4"
subprocess.run(
    [
        P["ffmpeg"] + "/bin/ffmpeg",
        "-nostdin",
        "-v",
        "error",
        "-f",
        "lavfi",
        "-i",
        "color=c=red:s=160x96:r=12:d=1",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=400:sample_rate=48000:duration=1",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-pix_fmt",
        "yuv420p",
        "-threads",
        "3",
        "-shortest",
        str(source),
    ],
    check=True,
)
a = cli("ingest", "reuse", str(source), wait=True)["assets"][0]["asset"]
calls = [
    {"tool": "open_project", "arguments": {"new": True}},
    {
        "tool": "execute_command",
        "arguments": {
            "command": "comp.new",
            "params": {
                "name": "Reusable",
                "width": 160,
                "height": 96,
                "frameRate": 12,
                "duration": 1,
            },
        },
    },
    {
        "tool": "execute_command",
        "arguments": {
            "command": "layer.newText",
            "params": {
                "text": "STORY",
                "size": 18,
                "fill": "#ffff00",
                "position": [80, 50],
            },
        },
    },
    {"tool": "save_project", "arguments": {"path": {"$workspace": "reusable.ecproj"}}},
    {
        "tool": "execute_command",
        "arguments": {
            "command": "renderQueue.add",
            "params": {
                "format": "prores",
                "proresProfile": "4444",
                "channels": "rgba",
                "output": {"$workspace": "overlay.mov"},
            },
        },
    },
    {
        "tool": "execute_command",
        "arguments": {"command": "renderQueue.render", "params": {"wait": True}},
    },
]
file = projects / "reuse/calls.json"
file.write_text(json.dumps(calls))
job = cli("native", "batch", "reuse", "effectcraft", str(file))
jobid = job["job"]
import time

for _ in range(120):
    state = cli("jobs", "status", jobid)
    if state["state"] in ["done", "failed", "interrupted", "cancelled"]:
        break
    time.sleep(0.1)
assert state["state"] == "done", state
asset = cli("native", "register", "reuse", jobid, "overlay.mov")
assert asset["kind"] == "generated"
assert asset["hash"] == hashlib.sha256(Path(asset["path"]).read_bytes()).hexdigest()
for project, filename in [
    ("other", "overlay.mov"),
    ("reuse", "../../red.mp4"),
    ("reuse", str(source)),
]:
    cli("native", "register", project, jobid, filename, success=False)
plan = {
    "version": 2,
    "output": {"width": 160, "height": 96, "fps": "12", "aspect": "5/3"},
    "clips": [
        {"asset": a, "in": "0", "out": "1", "reason": "preserved original"},
        {
            "asset": asset["asset"],
            "in": "0",
            "out": "1",
            "at": "0",
            "track": 2,
            "audio": False,
            "reason": "explicit registered native title",
        },
    ],
}
file = projects / "reuse/plan.json"
file.write_text(json.dumps(plan))
revision = cli("timeline", "apply", "reuse", str(file), wait=True)
preview = cli("preview", "reuse", "--seconds", "1", wait=True)
assert preview["qc"]["passed"]
Path(asset["path"]).write_bytes(
    Path(asset["path"]).read_bytes() + b"changed synthetic derived media"
)
error = cli(
    "preview",
    "reuse",
    "--out",
    "changed.mp4",
    "--seconds",
    "1",
    wait=True,
    success=False,
)
assert "asset changed" in error
Path("/fixture/acceptance.json").write_text(
    json.dumps(
        {
            "generated": asset,
            "nativeRevision": revision,
            "preview": preview,
            "foreignJobTraversalAbsoluteDenied": True,
            "modifiedDerivedDenied": True,
            "scope": "synthetic generated native media only",
        },
        indent=2,
    )
)
print(
    "PASS native generated asset promotion/reuse, foreign-job/traversal/absolute denial and derived identity corruption refusal"
)
