"""Scoped, network-disabled launcher for verified native Craft stdio servers; no tool replacement."""
import os
import re
import shlex
import signal
import subprocess
import sys
from pathlib import Path

from store import Policy, load_json


def light_report_pattern(root):
    return re.compile(re.escape(f"lightcraft-cli mcp: opened library {root / 'library'} (LoadReport {{ ") + r"snapshot_seq: [0-9]+, replayed: [0-9]+, stale: 0, failed: 0, torn_bytes: 0, torn_fragments: 0, damaged: None, created: (?:true|false), upgraded_from: None(?:, repaired: \[\])? \}\)\n")


def scoped_command(config, app, argv, root):
    policy = Policy({**config, "writeRoot": str(root)})
    if app == "photocraft":
        # Read real cgroup limits in this namespace, then shed setup privileges before the editor.
        setup = f'{shlex.quote(config["mount"])} -t cgroup2 -o ro,nosuid,nodev,noexec cgroup2 /sys/fs/cgroup\nexec {shlex.quote(config["setpriv"])} --bounding-set=-all --inh-caps=-all --ambient-caps=-all --no-new-privs "$@"'
        argv = [config["bash"], "-euc", setup, "--", *argv]
    command = policy.sandbox(argv, root)
    if app == "photocraft":
        command[1:1] = ["--uid", "0", "--gid", "0", "--cap-add", "CAP_SYS_ADMIN", "--cap-add", "CAP_SETPCAP", "--dir", "/sys/fs/cgroup"]
    for variable, directory in [("HOME", "home"), ("XDG_CONFIG_HOME", "config"), ("XDG_DATA_HOME", "data"), ("XDG_CACHE_HOME", "cache")]:
        path = policy.write(root / directory / ".keep").parent
        command[len(command) - len(argv):len(command) - len(argv)] = ["--setenv", variable, str(path)]
    return command


def main():
    if len(sys.argv) != 2:
        raise ValueError("usage: badwater-craft-mcp CONFIG.json")
    config = {**load_json(Path(os.environ["BADWATER_CRAFT_DEFAULTS"])), **load_json(Path(sys.argv[1]))}
    app = config["application"]
    supported = {"cadcraft", "deckcraft", "designcraft", "effectcraft", "filmcraft", "gridcraft", "lightcraft", "pdfcraft", "photocraft", "soundcraft", "vectorcraft", "wordcraft"}
    if app not in supported:
        raise ValueError("application has no verified native MCP interface")
    policy = Policy(config)
    root = policy.write(policy.write_root / app / ".keep").parent
    argv = [config["command"], "mcp"]
    if app == "pdfcraft":
        # Native confinement covers the private namespace, not the host root.
        argv += ["--root", "/"]
    if app in {"photocraft", "vectorcraft"}:
        argv += ["--automation-read-root", "/", "--automation-write-root", str(root)]
    if app == "vectorcraft":
        argv += ["--headless"]
    if app == "lightcraft":
        argv += ["--library", str(root / "library")]
    # The native child sees only its own application output tree, not sibling outputs.
    command = scoped_command(config, app, argv, root)
    expected = {
        "designcraft": [b"designcraft-cli: MCP server on stdio (headless (in-process engine, no window))\n"],
        "gridcraft": [b"gridcraft-cli: MCP server on stdio (headless (in-process engine, no window))\n"],
        "lightcraft": [b"lightcraft-cli mcp: serving MCP on stdio (headless)\n"],
        "pdfcraft": [b"pdfcraft-cli: MCP server on stdio (protocol 2025-06-18); close stdin to stop\n"],
        "vectorcraft": [(f"vectorcraft-cli: files confined: read /; write {root}\n").encode(), b"vectorcraft-cli: MCP server on stdio (headless)\n"],
    }.get(app, [])
    # Retain exact known informational startup lines locally, once only. Never mask warnings/errors.
    process = subprocess.Popen(command, stdin=sys.stdin.buffer, stdout=sys.stdout.buffer, stderr=subprocess.PIPE)
    stderr = process.stderr
    assert stderr is not None
    def stop(signum, _frame):
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(timeout=5)
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    light_report = light_report_pattern(root) if app == "lightcraft" else None
    with (root / "startup.log").open("ab") as log:
        for line in iter(lambda: stderr.readline(8192), b""):
            normal_load = light_report is not None and light_report.fullmatch(line.decode("utf-8", "replace")) is not None
            if line in expected or normal_load:
                if normal_load:
                    light_report = None
                else:
                    expected.remove(line)
                log.write(line); log.flush()
            else:
                sys.stderr.buffer.write(line); sys.stderr.buffer.flush()
    return process.wait(timeout=10)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
