#!/usr/bin/env python3
"""Explicit online release/dependency audit; no install or runtime execution.

Run from the repo: python3 tests/rea-audit.py > /outside/source/rea-audit.json
"""
import concurrent.futures
import datetime
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def metadata(name, version=""):
    with urllib.request.urlopen("https://registry.npmjs.org/" + name.replace("/", "%2f") + ("/" + version if version else ""), timeout=90) as response:
        return json.load(response)

lock = json.loads((ROOT / "pkgs/rea/package-lock.json").read_text())
source = (ROOT / "overlays/rea/default.nix").read_text()
parent = metadata("rea-agents")
version = parent["dist-tags"]["latest"]
assert re.fullmatch(r"\d+\.\d+\.\d+", version), version
published = parent["versions"][version]
assert lock["version"] == version
assert f'version = "{version}";' in source
assert f'hash = "{published["dist"]["integrity"]}";' in source
assert published["dist"]["tarball"] == f"https://registry.npmjs.org/rea-agents/-/rea-agents-{version}.tgz"
root = lock["packages"][""]
for field in ["dependencies", "engines"]:
    assert root[field] == published[field], field
assert not any(root.get(field) for field in ["devDependencies", "optionalDependencies"])
assert not any(key.endswith("node_modules/frida") for key in lock["packages"])

def check(item):
    key, package = item
    name = package.get("name") or key.rsplit("node_modules/", 1)[1]
    found = metadata(name, package["version"])
    for field in ["resolved", "integrity"]:
        upstream = "tarball" if field == "resolved" else field
        assert package[field] == found["dist"][upstream], (name, field)
    return {"name": name, "version": package["version"], "url": package["resolved"], "integrity": package["integrity"]}

with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
    tuples = list(executor.map(check, [(key, value) for key, value in lock["packages"].items() if key]))
print(json.dumps({"auditedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(), "name": "rea-agents", "version": version, "dist": published["dist"], "engines": root["engines"], "dependencies": tuples}, indent=2))
