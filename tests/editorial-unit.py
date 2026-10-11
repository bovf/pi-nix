"""Pure state/time/signal contracts, no host media/model/provider requests."""

import copy
import math
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
import numpy as np
import composition
import evidence
import editorial
from store import Policy, Project, atomic_json, digest, json_text


class EditorialContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        raw = root / "raw"
        raw.mkdir()
        self.config = {
            "readRoots": [str(raw)],
            "writeRoot": str(root / "projects"),
            "pipelineHash": "unit-pipeline",
            "modelHash": "unit-model",
        }
        self.policy = Policy(self.config)
        self.p = Project(self.policy, "unit", create=True)
        path = raw / "synthetic.mp4"
        path.write_bytes(b"unit synthetic, not valid media")
        self.asset = digest(path)
        s = path.stat()
        meta = {
            "duration": "20",
            "format": {"format_name": "mov,mp4"},
            "streams": [
                {"codec_type": "video", "width": 160, "height": 96},
                {"codec_type": "audio", "channels": 2},
            ],
        }
        with self.p.db() as db:
            db.execute(
                "INSERT INTO assets VALUES (?,?,?,?,?,?)",
                (
                    self.asset,
                    str(path),
                    self.asset,
                    s.st_size,
                    s.st_mtime_ns,
                    json_text(meta),
                ),
            )
        p = self.p
        cfg = self.config
        policy = self.policy

        class Engine:
            config = cfg

            def project(self, _):
                return p

        self.engine = Engine()
        self.engine.policy = policy
        self.plan = {
            "version": 2,
            "output": {"width": 160, "height": 96, "fps": "12", "aspect": "5/3"},
            "clips": [
                {
                    "asset": self.asset,
                    "in": "2",
                    "out": "6",
                    "reason": "complete source-backed thought",
                }
            ],
        }

    def tearDown(self):
        self.temp.cleanup()

    def cache(self):
        evidence.schema(self.p)
        body = {
            "asset": self.asset,
            "sourceHash": self.asset,
            "cacheKey": "unit-key",
            "pipelineHash": "unit-pipeline",
            "modelHash": "unit-model",
            "words": [
                {"id": 0, "start": "2", "end": "3", "text": "not", "probability": 0.8},
                {
                    "id": 1,
                    "start": "3",
                    "end": "4",
                    "text": "always",
                    "probability": 0.7,
                },
            ],
            "segments": [],
            "levels": [],
            "onsets": [],
            "motion": [],
            "candidates": [],
            "music": {"beats": []},
            "uncertainty": "ASR estimate",
        }
        path = self.policy.write(self.p.root / "evidence" / "unit.json")
        atomic_json(path, body)
        with self.p.db() as db:
            db.execute(
                "INSERT INTO editorial_evidence VALUES (?,?,?,?)",
                (self.asset, "unit-key", str(path), digest(path)),
            )
        return path

    def consent(self, allowed=True):
        with self.p.db() as db:
            db.execute(
                "UPDATE info SET value=? WHERE key='remoteConsent'",
                (json_text(allowed),),
            )

    def test_exact_speed_caption_time_map(self):
        self.plan["clips"][0]["speed"] = "2"
        self.plan["captions"] = {
            "words": [{"clip": 0, "in": "3", "out": "4", "text": "WORD"}]
        }
        v = self.p.validate(self.plan)
        self.assertEqual(v["duration"], "2")
        self.assertEqual(v["captionWords"][0]["at"], "1/2")
        self.assertEqual(v["captionWords"][0]["end"], "1")

    def test_rectangles_tracks_flags_and_gaps(self):
        for patch in [
            {"speed": True},
            {"audio": "false"},
            {"track": True},
            {"sourceRect": ["0", "0", "2", "1"]},
            {"at": "1"},
            {"positionKeys": [{"at": "-1", "x": 0.5, "y": 0.5}]},
        ]:
            p = copy.deepcopy(self.plan)
            p["clips"][0].update(patch)
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                self.p.validate(p)
        p = copy.deepcopy(self.plan)
        p["clips"].append(copy.deepcopy(p["clips"][0]))
        p["clips"][1]["at"] = "0"
        with self.assertRaises(ValueError):
            self.p.validate(p)

    def test_music_anchor_and_nan_bounds(self):
        self.plan["audioTracks"] = [
            {
                "asset": self.asset,
                "in": "1",
                "out": "5",
                "at": "0",
                "role": "music",
                "beatAnchor": {"source": "2", "timeline": "1", "tolerance": "1/12"},
            }
        ]
        self.p.validate(self.plan)
        self.plan["audioTracks"][0]["beatAnchor"]["timeline"] = "2"
        with self.assertRaises(ValueError):
            self.p.validate(self.plan)
        self.plan["audioTracks"][0].pop("beatAnchor")
        self.plan["audioTracks"][0]["gainDb"] = math.nan
        with self.assertRaises(ValueError):
            self.p.validate(self.plan)

    def test_subwords_timestamps_and_uncertainty(self):
        words = evidence.token_words(
            [
                {
                    "tokens": [
                        {"text": " amaz", "offsets": {"from": 0, "to": 100}, "p": 0.9},
                        {"text": "ing", "offsets": {"from": 100, "to": 300}, "p": 0.6},
                        {"text": "!", "offsets": {"from": 300, "to": 400}, "p": 0.8},
                    ]
                }
            ],
            28,
            Fraction(30),
        )
        self.assertEqual(len(words), 1)
        self.assertEqual(words[0]["text"], "amazing!")
        self.assertEqual(words[0]["start"], "28")
        self.assertEqual(words[0]["probability"], 0.6)

    def test_signal_and_beat_candidates(self):
        samples = np.zeros(16000 * 4, dtype=np.float32)
        for t in [0.5, 1, 1.5, 2, 2.5, 3, 3.5]:
            samples[int(t * 16000) : int(t * 16000) + 80] = 0.8
        levels, onsets = evidence.audio_features(samples, 0)
        self.assertEqual(len(levels), 8)
        self.assertGreaterEqual(len(onsets), 5)
        grid = evidence.music_grid(onsets)
        self.assertTrue(100 <= grid["bpmEstimate"] <= 140)
        self.assertEqual(evidence.music_grid([])["beats"], [])
        for opt in [
            {"transcribe": "false"},
            {"audioStream": True},
            {"visual": 1},
            {"profile": "unbounded"},
        ]:
            with self.assertRaises(ValueError):
                evidence.options(opt)

    def test_evidence_consent_corruption_and_auto_captions(self):
        path = self.cache()
        with self.assertRaises(ValueError):
            evidence.query(self.engine, "unit", self.asset, "unit-key")
        self.consent()
        self.assertEqual(
            len(
                evidence.query(
                    self.engine, "unit", self.asset, "unit-key", start="2", end="5"
                )["entries"]
            ),
            2,
        )
        self.plan["captions"] = {
            "fromEvidence": {"asset": self.asset, "cacheKey": "unit-key"}
        }
        self.assertEqual(len(self.p.validate(self.plan)["captionWords"]), 2)
        path.write_text("{}")
        with self.assertRaises(ValueError):
            evidence.read(self.engine, "unit", self.asset, "unit-key")

    def test_source_backed_context_and_duplicate_batches(self):
        self.cache()
        self.consent()
        note = {
            "asset": self.asset,
            "in": "2",
            "out": "4",
            "kind": "quote",
            "summary": "The qualifier not is essential",
            "cacheKey": "unit-key",
            "wordIds": [0, 1],
        }
        key = editorial.annotate(self.engine, "unit", note)["context"]
        self.assertEqual(
            len(editorial.contexts(self.engine, "unit", self.asset)["contexts"]), 1
        )
        self.assertEqual(
            len(editorial.search(self.engine, "unit", "qualifier")["contexts"]), 1
        )
        item = {
            "name": "short1",
            "title": "Complete idea",
            "plan": self.plan,
            "contexts": [key],
        }
        self.assertEqual(
            editorial.save_batch(
                self.engine, "unit", "batch", [item], "Preserve the complete thought"
            )["deliverables"],
            1,
        )
        with self.assertRaises(ValueError):
            editorial.save_batch(
                self.engine,
                "unit",
                "duplicate",
                [item, {**item, "name": "short2"}],
                "Do not repeat excerpts",
            )
        with self.assertRaises(ValueError):
            editorial.annotate(self.engine, "unit", {**note, "wordIds": [99]})
        for preview, approved in [(False, False), (False, "true"), (1, True)]:
            with self.assertRaises(ValueError):
                editorial.batch_start(self.engine, "unit", "batch", preview, approved)
        self.consent(False)
        with self.assertRaises(ValueError):
            editorial.contexts(self.engine, "unit", self.asset)

    def test_duck_curve_merges_speech_and_carries_window_boundaries(self):
        clip = {"in": "0", "out": "240", "at": "0", "role": "music"}
        curve = composition.duck_curve(
            clip, [{"at": "119", "end": "120"}, {"at": "120", "end": "121"}]
        )
        self.assertEqual(composition.curve_at(curve, Fraction(120)), -12)
        self.assertEqual(composition.curve_at(curve, Fraction(125)), 0)

    def test_editorial_boundary_findings(self):
        self.cache()
        self.plan["clips"][0]["in"] = "5/2"
        result = editorial.check(self.engine, "unit", self.plan)
        self.assertFalse(result["mechanicalPassed"])
        self.assertFalse(result["editorialQualityCertified"])


if __name__ == "__main__":
    unittest.main()
