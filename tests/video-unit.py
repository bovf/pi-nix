"""Fast pure state/security/plan unit tests. Native runtime proof is a separate gate."""
import json
import os
import sqlite3
import tempfile
import unittest
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

from store import Policy, Project, atomic_json, digest, identifier, json_text, publish, rational


class StateContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.raw = self.root / "raw"
        self.raw.mkdir()
        self.policy = Policy({"readRoots": [str(self.raw)], "writeRoot": str(self.root / "derived")})
        self.project = Project(self.policy, "test", create=True)
        self.source = self.raw / "a name; $(never-a-command).mp4"
        self.source.write_bytes(b"unit-test data, NOT a native media fixture")
        self.asset = digest(self.source)
        self.metadata = {"duration": "4", "streams": [{"codec_type": "video", "time_base": "1/30000", "avg_frame_rate": "30000/1001"}, {"codec_type": "audio"}]}
        s = self.source.stat()
        with self.project.db() as db:
            db.execute("INSERT INTO assets VALUES (?,?,?,?,?,?)", (self.asset, str(self.source), self.asset, s.st_size, s.st_mtime_ns, json_text(self.metadata)))
        self.plan = {"version": 1, "output": {"width": 160, "height": 90, "fps": "30000/1001", "aspect": "16/9"},
                     "clips": [{"asset": self.asset, "in": "1/2", "out": "3/2", "reason": "explicit unit-test range"}],
                     "constraints": {"targetDuration": "1", "tolerance": "0", "mustInclude": [{"asset": self.asset, "in": "1", "out": "3/2"}], "mustExclude": [{"asset": self.asset, "in": "2", "out": "3"}]}}

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_rational_times(self):
        self.assertEqual(rational("30000/1001"), Fraction(30000, 1001))
        self.assertEqual(rational("0.1"), Fraction(1, 10))
        for value in [True, 0.1, float("nan"), float("inf"), "NaN", "Infinity", "1/0", "x" * 100]:
            with self.assertRaises((ValueError, ZeroDivisionError)):
                rational(value)
        self.assertEqual(self.project.validate(self.plan)["duration"], "1")

    def test_content_identity_and_changed_asset(self):
        self.project.asset(self.asset, verify=True)
        before = self.source.stat()
        b = self.source.read_bytes()
        self.source.write_bytes(b.replace(b"unit", b"fake"))
        os.utime(self.source, ns=(before.st_atime_ns, before.st_mtime_ns))
        with self.assertRaisesRegex(ValueError, "changed"):
            self.project.asset(self.asset, verify=True)

    def test_traversal_and_symlinks(self):
        for value in [self.root / "secret", self.raw / ".." / "secret", "https://example.invalid/media.mp4"]:
            with self.assertRaises(ValueError):
                self.policy.read(value, raw=True)
        link = self.raw / "link.mp4"
        link.symlink_to(self.source)
        with self.assertRaisesRegex(ValueError, "symlinks"):
            self.policy.read(link, raw=True)
        escape = self.project.root / "escape"
        escape.symlink_to(self.raw, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlinks"):
            self.policy.write(escape / "a.mp4")

    def test_disjoint_authority(self):
        for output in [self.raw, self.raw / "derived", self.root]:
            with self.assertRaisesRegex(ValueError, "disjoint"):
                Policy({"readRoots": [str(self.raw)], "writeRoot": str(output)})
        with self.assertRaises(ValueError):
            identifier("../another-project")
        with self.assertRaises(ValueError):
            Policy({"readRoots": ["/"], "writeRoot": str(self.root / "derived")})

    def test_plan_rejections(self):
        cases = []
        for version in [True, 1.0, "1", None, 2]:
            p = deepcopy(self.plan); p["version"] = version; cases.append(p)
        p = deepcopy(self.plan); p["clips"][0]["out"] = "5"; cases.append(p)
        p = deepcopy(self.plan); p["clips"][0]["in"] = "-1"; cases.append(p)
        p = deepcopy(self.plan); p["output"]["fps"] = "0"; cases.append(p)
        p = deepcopy(self.plan); p["output"]["width"] = 161; cases.append(p)
        p = deepcopy(self.plan); p["output"]["aspect"] = "9/16"; cases.append(p)
        p = deepcopy(self.plan); p["clips"][0]["reason"] = ""; cases.append(p)
        p = deepcopy(self.plan); p["captions"] = True; cases.append(p)
        p = deepcopy(self.plan); p["constraints"]["targetDuration"] = "2"; cases.append(p)
        p = deepcopy(self.plan); p["constraints"]["mustInclude"][0]["out"] = "2"; cases.append(p)
        p = deepcopy(self.plan); p["constraints"]["mustExclude"][0]["in"] = "1"; cases.append(p)
        p = deepcopy(self.plan); p["constraints"]["maxCutSeconds"] = "1/2"; cases.append(p)
        p = deepcopy(self.plan); p["clips"][0]["in"] = True; cases.append(p)
        p = deepcopy(self.plan); p["audio"] = {"microphone": self.asset, "offset": "-1"}; cases.append(p)
        for plan in cases:
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                self.project.validate(plan)

    def test_include_union_and_order(self):
        p = deepcopy(self.plan)
        p["clips"] = [{"asset": self.asset, "in": "1", "out": "3/2", "reason": "second first"}, {"asset": self.asset, "in": "1/2", "out": "1", "reason": "first second"}]
        p["constraints"]["mustInclude"] = [{"asset": self.asset, "in": "1/2", "out": "3/2"}]
        result = self.project.validate(p)
        self.assertEqual([r["timelineIn"] for r in result["ranges"]], ["0", "1/2"])

    def test_atomic_no_clobber_and_hardlinks(self):
        target = self.policy.write(self.project.root / "data.json")
        atomic_json(target, {"previous": True})
        before = target.read_bytes()
        with self.assertRaises(FileExistsError):
            atomic_json(target, {"bad": "overwrite"})
        self.assertEqual(target.read_bytes(), before)
        hard = self.project.root / "alias.json"
        os.link(target, hard)
        with self.assertRaisesRegex(ValueError, "linked"):
            atomic_json(target, {"overwrite": True}, replace=True)
        self.assertEqual(target.read_bytes(), before)
        hard.unlink()
        atomic_json(target, {"explicit": "replacement"}, replace=True)
        self.assertEqual(json.loads(target.read_text()), {"explicit": "replacement"})

    def test_versioned_sqlite_and_privacy_default(self):
        self.assertEqual(self.project.summary()["indexVersion"], 1)
        self.assertFalse(self.project.summary()["remoteConsent"])
        self.assertEqual(self.project.path.stat().st_mode & 0o777, 0o600)
        with self.project.db() as db:
            db.execute("PRAGMA user_version=99")
        with self.assertRaisesRegex(ValueError, "unsupported index version"):
            Project(self.policy, "test")
        self.assertTrue(self.project.path.is_file())


if __name__ == "__main__":
    unittest.main()
