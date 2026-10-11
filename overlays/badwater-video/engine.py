"""One local engine shared by the CLI and MCP frontends. Observations are data, not instructions."""
import hashlib
import json
import math
import re
import uuid
from fractions import Fraction
from pathlib import Path

from jobs import Jobs
from native import NativeMCP
from store import (MEDIA_EXTENSIONS, PIPELINE, TICKS, Policy, Project, atomic_json,
                   digest, identifier, json_text, load_json, no_links, publish, rational)


class Engine:
    def __init__(self, config, config_path):
        self.config = config
        self.policy = Policy(config)
        self.config_path = config_path
        self.jobs = Jobs(self.policy, config_path)

    def project(self, project, create=False):
        return Project(self.policy, project, create=create)

    def create(self, project):
        return self.project(project, create=True).summary()

    def privacy(self, project, allow_remote):
        if type(allow_remote) is not bool:
            raise ValueError("consent must be an explicit boolean after user permission")
        p = self.project(project)
        with p.db() as db:
            db.execute("UPDATE info SET value=? WHERE key='remoteConsent'", (json_text(allow_remote),))
        return {"project": project, "remoteConsent": allow_remote, "scope": "frames and transcript snippets sent through Pi to its configured model; no direct provider client"}

    def probe(self, path):
        self.policy.read(path, raw=True)
        stdout, _ = self.policy.run([self.config["ffprobe"], "-v", "error", "-show_entries",
            "format=duration,format_name:stream=index,codec_type,codec_name,width,height,avg_frame_rate,r_frame_rate,time_base,duration_ts,duration,sample_rate,channels,start_time",
            "-of", "json", str(path)], timeout=30)
        data = json.loads(stdout)
        streams = data.get("streams", [])
        if not streams or not any(s.get("codec_type") in {"audio", "video"} for s in streams):
            raise ValueError("asset has no supported audio/video stream")
        durations = [Fraction(str(s["duration_ts"])) * Fraction(s["time_base"]) for s in streams if s.get("duration_ts") is not None and s.get("time_base")]
        if data.get("format", {}).get("duration") is not None:
            durations.append(Fraction(data["format"]["duration"]))
        data["duration"] = str(max(durations, default=Fraction(0)))
        data["timestampConvention"] = "seconds relative to source; stream time_base and nominal/average frame rates retained; VFR is never inferred from frame count"
        return data

    def ingest(self, project, paths):
        self.project(project)
        if not isinstance(paths, list) or not 1 <= len(paths) <= 1000:
            raise ValueError("ingest accepts 1..1000 explicit files; directory enumeration must be user-authorized")
        for value in paths:
            p = self.policy.read(value, raw=True)
            if p.suffix.lower() not in MEDIA_EXTENSIONS:
                raise ValueError("unsupported media extension (playlists, projects and network references are not ingestible assets)")
        return self.jobs.submit(project, "ingest", {"paths": paths})

    def _ingest(self, project, args, job):
        p = self.project(project)
        result = []
        for i, value in enumerate(args["paths"]):
            path = self.policy.read(value, raw=True)
            metadata = self.probe(path)
            before = path.stat()
            h = digest(path)
            after = path.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError("source changed during ingest")
            with p.db() as db:
                existing = db.execute("SELECT * FROM assets WHERE id=?", (h,)).fetchone()
                if existing is None:
                    db.execute("INSERT INTO assets VALUES (?,?,?,?,?,?)", (h, str(path), h, after.st_size, after.st_mtime_ns, json_text(metadata)))
                elif existing["path"] == str(path):
                    db.execute("UPDATE assets SET size=?,mtime_ns=? WHERE id=?", (after.st_size, after.st_mtime_ns, h))
            result.append({"asset": h, "hash": h, "path": str(path), "metadata": metadata, "reusedIdentity": existing is not None})
            self.jobs.update(job, progress=(i + 1) / len(args["paths"]))
        return {"assets": result, "originalsWritten": False}

    def assets(self, project, limit=20, offset=0):
        if type(limit) is not int or type(offset) is not int or not 1 <= limit <= 100 or offset < 0:
            raise ValueError("asset pages require limit 1..100 and a nonnegative offset")
        p = self.project(project)
        with p.db() as db:
            rows = [dict(r) for r in db.execute("SELECT id,path,size,metadata FROM assets ORDER BY id LIMIT ? OFFSET ?", (limit, offset))]
        for row in rows:
            row["metadata"] = json.loads(row["metadata"])
            try:
                p.asset(row["id"])
                row["state"] = "current"
            except ValueError:
                row["state"] = "changed-or-missing"
        return {"assets": rows}

    def cache_key(self, options):
        return hashlib.sha256(json_text({"pipeline": PIPELINE, "pipelineHash": self.config["pipelineHash"], "model": self.config["modelHash"], "whisper": self.config["whisper"], "ffmpeg": self.config["ffmpeg"], "options": options}).encode()).hexdigest()

    @staticmethod
    def analysis_options(options):
        defaults = {"language": "en", "transcribe": True, "maxFrames": 8, "sceneThreshold": "0.35", "silenceDb": -35}
        if set(options) - set(defaults):
            raise ValueError("unknown analysis configuration")
        out = {**defaults, **options}
        if out["language"] != "en" or type(out["transcribe"]) is not bool:
            raise ValueError("the pinned tiny.en model supports English only; transcribe is boolean")
        if type(out["maxFrames"]) is not int or not 1 <= out["maxFrames"] <= 16 or not 0 <= rational(out["sceneThreshold"]) <= 1 or not -60 <= out["silenceDb"] <= -10:
            raise ValueError("analysis bounds are invalid")
        return out

    def analyze(self, project, asset, options):
        p = self.project(project)
        p.asset(asset)
        options = self.analysis_options(options)
        key = self.cache_key(options)
        with p.db() as db:
            cached = db.execute("SELECT body FROM observations WHERE asset=? AND cache_key=?", (asset, key)).fetchone()
        return {**self.jobs.submit(project, "analyze", {"asset": asset, "options": options}), "cachedHint": cached is not None, "cacheKey": key}

    def _frame(self, p, asset, when, destination):
        a = p.asset(asset)
        t = rational(when)
        duration = rational(a["metadata"]["duration"])
        if t < 0 or (duration and t >= duration):
            raise ValueError("frame request is outside source duration")
        _, stderr = self.policy.run([self.config["ffmpeg"], "-nostdin", "-nostats", "-v", "info", "-copyts", "-ss", str(float(t)), "-i", a["path"],
                                    "-frames:v", "1", "-vf", "showinfo,scale='min(640,iw)':-2", "-threads", "3", str(destination)], timeout=30)
        if not destination.is_file() or destination.stat().st_size > 1_000_000:
            raise ValueError("frame extraction produced no bounded image")
        pts = re.search(rb"\bn:\s*0\b.*?pts_time:([\d.eE+-]+)", stderr)
        return {"asset": asset, "requestedSeconds": str(t), "decodedPtsSeconds": pts.group(1).decode() if pts else None,
                "path": str(destination), "hash": digest(destination), "provenance": "FFmpeg decoded frame, not a semantic event label"}

    def inspect(self, project, asset, when, share_with_model=False, local=False, refresh=False):
        p = self.project(project)
        p.asset(asset, verify=True)
        if share_with_model and not p.summary()["remoteConsent"] and not local:
            raise ValueError("obtain explicit permission and set project privacy before sending footage-derived frames to Pi's model")
        key = hashlib.sha256((asset + ":" + str(rational(when)) + ":" + self.config["ffmpeg"] + ":" + self.config["pipelineHash"]).encode()).hexdigest()
        path = self.policy.write(p.root / "frames" / (key + ".png"))
        record = path.with_suffix(".json")
        if path.exists() and record.exists():
            try:
                result = load_json(self.policy.read(str(record)))
                if result["asset"] != asset or result["path"] != str(path) or rational(result["requestedSeconds"]) != rational(when):
                    raise ValueError("cached frame metadata differs from its authorized identity")
                if digest(path) != result["hash"]:
                    raise ValueError("cached frame was modified")
                return {**result, "cached": True, "shareWithModel": share_with_model}
            except (ValueError, OSError, KeyError, TypeError):
                if not refresh:
                    raise
        if refresh:
            # Keep invalid/orphaned derived bytes for inspection; never clean up/delete caches.
            for artifact in [path, record]:
                if artifact.exists():
                    artifact.rename(artifact.with_name(artifact.name + ".invalid-" + uuid.uuid4().hex))
        temp = path.with_name("." + key + "." + uuid.uuid4().hex + ".png")
        result = self._frame(p, asset, when, temp)
        publish(temp, path)
        result["path"] = str(path)
        atomic_json(record, result)
        return {**result, "cached": False, "shareWithModel": share_with_model}

    def _analyze(self, project, args, job):
        p = self.project(project)
        a = p.asset(args["asset"], verify=True)
        options = self.analysis_options(args["options"])
        key = self.cache_key(options)
        with p.db() as db:
            cached = db.execute("SELECT body FROM observations WHERE asset=? AND cache_key=?", (a["id"], key)).fetchone()
        if cached:
            try:
                body = self.analysis_body(p, a["id"], key)
                return {"cached": True, "asset": a["id"], "cacheKey": key, "summary": body["summary"]}
            except (ValueError, OSError, KeyError, TypeError):
                # Preserve invalid derived evidence; regenerate, never trust stale query rows.
                previous = self.policy.write(p.root / "analysis" / a["id"] / key / "observations.json")
                if previous.exists():
                    previous.rename(previous.with_name(previous.name + ".invalid-" + uuid.uuid4().hex))
                with p.db() as db:
                    db.execute("DELETE FROM observations WHERE asset=? AND cache_key=?", (a["id"], key))
                    db.execute("DELETE FROM transcript WHERE asset=? AND cache_key=?", (a["id"], key))
        root = self.policy.write(p.root / "analysis" / a["id"] / key / "observations.json").parent
        duration = rational(a["metadata"]["duration"])
        if duration > 4 * 3600:
            raise ValueError("analysis is bounded to four hours per source; split authorized recordings explicitly")
        has_audio = any(s["codec_type"] == "audio" for s in a["metadata"]["streams"])
        has_video = any(s["codec_type"] == "video" for s in a["metadata"]["streams"])
        transcript, audio, scenes, frames = [], {}, [], []
        if has_audio:
            _, log = self.policy.run([self.config["ffmpeg"], "-nostdin", "-nostats", "-v", "info", "-i", a["path"], "-vn", "-af",
                f"astats=metadata=0:reset=0,silencedetect=noise={options['silenceDb']}dB:d=0.3", "-f", "null", "-"], timeout=self.config.get("timeoutSeconds", 1200))
            text = log.decode("utf-8", "replace")
            values = lambda name: re.findall(re.escape(name) + r":\s*(-?\d+(?:\.\d+)?|-inf|inf)", text)
            audio = {"peakDbFS": values("Peak level dB")[-1:] or None, "rmsDbFS": values("RMS level dB")[-1:] or None,
                     "silenceStartsSeconds": values("silence_start")[:1000], "silenceEndsSeconds": values("silence_end")[:1000],
                     "silenceThresholdDbFS": options["silenceDb"], "kind": "algorithmic signal measurements; silence is not an editorial deletion decision"}
        if has_audio and options["transcribe"]:
            if digest(Path(self.config["model"])) != self.config["modelHash"]:
                raise ValueError("Whisper model content differs from its pinned SHA-256")
            chunks = max(1, math.ceil(duration / 30))
            for i in range(chunks):
                wav = root / f"speech-{i:04d}.wav"
                self.policy.run([self.config["ffmpeg"], "-nostdin", "-y", "-v", "error", "-ss", str(i * 30), "-i", a["path"],
                                 "-t", "30", "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)])
                output = root / f"speech-{i:04d}"
                self.policy.run([self.config["whisper"], "-m", self.config["model"], "-f", str(wav), "-l", "en", "-t", "3", "-ng", "-ojf", "-of", str(output)], timeout=180)
                body = load_json(output.with_suffix(".json"))
                for segment in body["transcription"]:
                    start = Fraction(i * 30) + Fraction(segment["offsets"]["from"], 1000)
                    end = min(duration, Fraction(i * 30) + Fraction(segment["offsets"]["to"], 1000))
                    if end > start:
                        transcript.append({"start": str(start), "end": str(end), "text": segment["text"][:4000],
                                           "provenance": "Whisper tiny.en model-estimated segment timestamps; end clamped to media duration", "confidence": None})
                self.jobs.update(job, progress=0.1 + 0.6 * (i + 1) / chunks)
        if has_video and duration > 0:
            _, log = self.policy.run([self.config["ffmpeg"], "-nostdin", "-nostats", "-v", "info", "-i", a["path"], "-an", "-vf",
                f"select='gt(scene,{float(rational(options['sceneThreshold']))})',showinfo", "-frames:v", "32", "-f", "null", "-"], timeout=self.config.get("timeoutSeconds", 1200))
            scenes = [str(Fraction(x.decode())) for x in re.findall(rb"pts_time:([\d.eE+-]+)", log)[:32]]
            candidates = {Fraction(0), duration / 2, max(Fraction(0), duration - Fraction(1, 2))}
            for cut in scenes:
                t = rational(cut)
                candidates.update({max(Fraction(0), t - Fraction(1, 10)), min(duration - Fraction(1, 1000), t + Fraction(1, 10))})
            anchors = sorted({Fraction(0), duration / 2, max(Fraction(0), duration - Fraction(1, 2))})[:options["maxFrames"]]
            remaining = sorted(candidates - set(anchors))
            budget = options["maxFrames"] - len(anchors)
            selected = anchors + ([remaining[round(i * (len(remaining) - 1) / max(1, budget - 1))] for i in range(min(budget, len(remaining)))] if remaining and budget else [])
            for i, t in enumerate(sorted(set(selected))):
                if t < duration:
                    frames.append(self.inspect(project, a["id"], str(t), local=True, refresh=True))
                    self.jobs.update(job, progress=0.75 + 0.2 * (i + 1) / options["maxFrames"])
        p.asset(a["id"], verify=True)
        body = {"asset": a["id"], "cacheKey": key, "pipeline": PIPELINE, "pipelineHash": self.config["pipelineHash"], "modelHash": self.config["modelHash"], "configuration": options,
                "transcript": transcript, "sceneBoundariesSeconds": scenes, "frames": frames, "audio": audio,
                "summary": {"transcriptSegments": len(transcript), "frames": len(frames), "sceneCandidates": len(scenes)},
                "understanding": "lexical transcript and sampled audiovisual/signal observations only; no speaker identities, embeddings, semantic search or continuous comprehension"}
        if len(json_text(body).encode("utf-8")) > 16 * 1024 * 1024:
            raise ValueError("analysis observations exceed 16 MiB; split authorized recordings explicitly")
        atomic_json(root / "observations.json", body, replace=True)
        with p.db() as db:
            db.execute("INSERT OR REPLACE INTO observations VALUES (?,?,?)", (a["id"], key, json_text(body)))
            db.execute("DELETE FROM transcript WHERE asset=? AND cache_key=?", (a["id"], key))
            db.executemany("INSERT INTO transcript(asset,cache_key,start,end,text) VALUES (?,?,?,?,?)", [(a["id"], key, r["start"], r["end"], r["text"]) for r in transcript])
        return {"asset": a["id"], "cached": False, "cacheKey": key, "summary": body["summary"], "observationsPath": str(root / "observations.json")}

    def analysis_body(self, p, asset, key):
        identifier(key)
        with p.db() as db:
            row = db.execute("SELECT body FROM observations WHERE asset=? AND cache_key=?", (asset, key)).fetchone()
        if row is None or len(row[0].encode("utf-8")) > 16 * 1024 * 1024:
            raise ValueError("analysis cache is missing or exceeds 16 MiB; analyze again")
        body = json.loads(row[0])
        if body["asset"] != asset or body["pipelineHash"] != self.config["pipelineHash"] or body["modelHash"] != self.config["modelHash"] or self.cache_key(body["configuration"]) != key:
            raise ValueError("analysis cache belongs to a stale model/pipeline/configuration; analyze again")
        path = self.policy.read(str(p.root / "analysis" / asset / key / "observations.json"))
        if path.stat().st_size > 16 * 1024 * 1024 or path.stat().st_nlink != 1 or json.loads(path.read_text()) != body:
            raise ValueError("analysis cache was modified or exceeds its bound; analyze again")
        for frame in body["frames"]:
            frame_key = hashlib.sha256((asset + ":" + str(rational(frame["requestedSeconds"])) + ":" + self.config["ffmpeg"] + ":" + self.config["pipelineHash"]).encode()).hexdigest()
            if frame["asset"] != asset or frame["path"] != str(p.root / "frames" / (frame_key + ".png")):
                raise ValueError("analysis frame reference differs from its authorized identity")
            record = self.policy.read(str(Path(frame["path"]).with_suffix(".json")))
            expected_record = {k: v for k, v in frame.items() if k not in {"cached", "shareWithModel"}}
            if record.stat().st_nlink != 1 or load_json(record) != expected_record or digest(self.policy.read(frame["path"])) != frame["hash"]:
                raise ValueError("analysis frame cache was modified; analyze again")
        return body

    def search(self, project, query, limit=10, local=False):
        if not isinstance(query, str) or not 1 <= len(query) <= 200 or type(limit) is not int or not 1 <= limit <= 20:
            raise ValueError("search requires a bounded literal phrase and limit 1..20")
        p = self.project(project)
        phrase = '"' + query.replace('"', '""') + '"'
        with p.db() as db:
            rows = [dict(r) for r in db.execute("SELECT asset,cache_key,start,end,text FROM transcript WHERE transcript MATCH ? LIMIT ?", (phrase, limit))]
        current, verified = [], set()
        for row in rows:
            try:
                p.asset(row["asset"])
                identity = (row["asset"], row["cache_key"])
                if identity not in verified:
                    self.analysis_body(p, *identity)
                    verified.add(identity)
                current.append(row)
            except (ValueError, OSError, KeyError, TypeError):
                continue
        permitted = local or p.summary()["remoteConsent"]
        if not permitted:
            current = [{k: v for k, v in r.items() if k != "text"} for r in current]
        return {"matches": current, "searchKind": "literal transcript phrase (not multimodal semantic search)", "transcriptTextWithheldUntilConsent": not permitted}

    def observations(self, project, asset, cache_key, start="0", end="30", limit=10, local=False):
        p = self.project(project)
        p.asset(asset)
        result = self.analysis_body(p, asset, cache_key)
        a, b = rational(start), rational(end)
        if not 0 <= a < b or b - a > 120 or type(limit) is not int or not 1 <= limit <= 20:
            raise ValueError("observation queries need a window of at most 120 seconds and limit 1..20")
        result["transcript"] = [r for r in result["transcript"] if rational(r["start"]) < b and rational(r["end"]) > a][:limit]
        result["sceneBoundariesSeconds"] = [r for r in result["sceneBoundariesSeconds"] if a <= rational(r) < b][:limit]
        result["frames"] = [r for r in result["frames"] if a <= rational(r["requestedSeconds"]) < b][:min(limit, 16)]
        for field in ["silenceStartsSeconds", "silenceEndsSeconds"]:
            if field in result["audio"]:
                result["audio"][field] = [r for r in result["audio"][field] if a <= rational(r) < b][:limit]
        result["window"] = {"start": str(a), "end": str(b), "limit": limit}
        if not local and not p.summary()["remoteConsent"]:
            result.pop("transcript")
            result["privacy"] = "transcript text withheld until explicit permission"
        return result

    def validate(self, project, plan):
        return self.project(project).validate(plan)

    def apply(self, project, plan):
        self.validate(project, plan)
        return self.jobs.submit(project, "apply", {"plan": plan})

    def _audio_segment(self, source, start, duration, work, index):
        if duration > 120:
            raise ValueError("dedicated audio cuts are bounded to 120 seconds to avoid whole-recording native audio imports")
        wav = work / f"audio-source-{index}.wav"
        self.policy.run([self.config["ffmpeg"], "-nostdin", "-v", "error", "-ss", str(float(start)), "-i", source,
                         "-t", str(float(duration)), "-vn", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(wav)])
        return wav

    def _sound_segment(self, p, source, start, duration, work, index, stderr):
        if not self.config.get("soundcraft"):
            raise ValueError("requested speech normalization requires the verified SoundCraft selection")
        wav = self._audio_segment(source, start, duration, work, index)
        with NativeMCP(self.policy.sandbox([self.config["soundcraft"], "mcp"], work), stderr) as sound:
            sound.tool("new_session", {"name": f"Speech cut {index}"})
            imported = sound.tool("import_audio", {"path": str(wav)})
            measure = sound.tool("bounce_mix", {"path": str(work / f"measure-{index}.wav"), "start": {"seconds": 0}, "end": {"seconds": float(duration)}, "normalize": False})
            if not all(math.isfinite(float(measure[x])) for x in ["lufs", "true_peak_db"]):
                raise ValueError("cannot normalize silent/non-finite audio; review this source explicitly")
            gain = min(-16 - float(measure["lufs"]), -1 - float(measure["true_peak_db"]), 20)
            sound.tool("execute", {"command": "clip.gain", "params": {"clips": [r["clip"] for r in imported["imported"]], "db": gain}})
            output = work / f"normalized-{index}.wav"
            measured = sound.tool("bounce_mix", {"path": str(output), "start": {"seconds": 0}, "end": {"seconds": float(duration)}, "normalize": False})
            sound.tool("save_session", {"path": str(work / f"audio-{index}.scraft")})
        return output, {"backend": "SoundCraft native clip gain and bounce", "gainDb": gain, "targetLufs": -16, "peakCeilingDb": -1, "measured": measured, "scope": "mono speech cut; no automatic mixing, music or interpretation"}

    def _apply(self, project, args, job):
        p = self.project(project)
        plan = args["plan"]
        validation = p.validate(plan)
        sources = {r["asset"]: p.asset(r["asset"], verify=True) for r in validation["ranges"]}
        audio = validation["audio"]
        if "microphone" in audio:
            sources[audio["microphone"]] = p.asset(audio["microphone"], verify=True)
        work = self.policy.write(p.root / ".work" / job / "native.fcproj").parent
        for executable in [self.config.get("filmcraft"), self.config.get("soundcraft") if audio.get("normalize") else self.config.get("filmcraft")]:
            if not executable or not Path(executable).is_file():
                raise ValueError("the required native editor executable is not configured")
        sound_results = []
        movie_sources = {r["asset"]: sources[r["asset"]] for r in validation["ranges"]}
        for source in movie_sources.values():
            actual = self.probe(Path(source["path"]))
            if not set(actual["format"]["format_name"].split(",")) & {"mov", "mp4", "matroska", "webm"}:
                raise ValueError("native streaming timeline import supports verified MP4/MOV/Matroska/WebM containers; other indexed formats need an explicitly authorized proxy, not an unbounded whole-file import")
        with (work / "native.stderr").open("w") as stderr:
            with NativeMCP(self.policy.sandbox([self.config["filmcraft"], "mcp"], work), stderr) as film:
                film.tool("command_run", {"id": "file.newProject", "params": {"name": project}})
                settings = validation["output"]
                film.tool("command_run", {"id": "file.newSequence", "params": {"name": project, "width": settings["width"], "height": settings["height"], "fps": float(rational(settings["fps"])), "video": 1, "audio": 1}})
                paths = [a["path"] for a in movie_sources.values()]
                imported = film.tool("command_run", {"id": "file.import", "params": {"paths": paths}})
                media_ids = dict(zip(movie_sources, imported["items"], strict=True))
                for index, cut in enumerate(validation["ranges"]):
                    start, end, dest = rational(cut["in"]), rational(cut["out"]), rational(cut["timelineIn"])
                    separate = "microphone" in audio or audio.get("normalize", False)
                    film.tool("command_run", {"id": "timeline.place", "params": {"item": media_ids[cut["asset"]], "track": "V1", "audioTrack": "A1", "time": round(dest * TICKS), "sourceIn": round(start * TICKS), "duration": round((end - start) * TICKS), "video": True, "audio": not separate}})
                    if separate:
                        source_id = audio.get("microphone", cut["asset"])
                        source_in = start + rational(audio.get("offset", "0"))
                        if audio.get("normalize"):
                            extracted, result = self._sound_segment(p, sources[source_id]["path"], source_in, end - start, work, index, stderr)
                            sound_results.append(result)
                        else:
                            extracted = self._audio_segment(sources[source_id]["path"], source_in, end - start, work, index)
                        item = film.tool("command_run", {"id": "file.import", "params": {"paths": [str(extracted)]}})["items"][0]
                        source_in = Fraction(0)
                        film.tool("command_run", {"id": "timeline.place", "params": {"item": item, "track": "A1", "time": round(dest * TICKS), "sourceIn": round(source_in * TICKS), "duration": round((end - start) * TICKS), "video": False, "audio": True}})
                    self.jobs.update(job, progress=0.1 + 0.7 * (index + 1) / len(validation["ranges"]))
                # The pinned native command performs conservative fit/letterbox conforming.
                placed = film.tool("sequence_inspect", {})
                video_clips = [c["clip"] for track in placed["video"] for c in track["items"]]
                film.tool("command_run", {"id": "clip.fitToFrame", "params": {"clips": video_clips}})
                native = work / "native.fcproj"
                film.tool("command_run", {"id": "file.saveAs", "params": {"path": str(native)}})
                reopened = film.tool("command_run", {"id": "file.open", "params": {"path": str(native)}})
                if reopened.get("missingMedia"):
                    raise ValueError("native project reopened with missing media")
                inspection = film.tool("sequence_inspect", {})
                actual = [c for track in inspection["video"] for c in track["items"]]
                expected_ranges = validation["ranges"]
                if len(actual) != len(expected_ranges):
                    raise ValueError("native timeline cut count differs from the validated plan")
                tolerance = round(TICKS / rational(settings["fps"]))
                for observed, expected in zip(actual, expected_ranges, strict=True):
                    if observed["item"] != media_ids[expected["asset"]] or any(abs(observed[key] - round(rational(expected[value]) * TICKS)) > tolerance for key, value in [("start", "timelineIn"), ("sourceIn", "in"), ("sourceOut", "out")]):
                        raise ValueError("native timeline source/range/order differs from the validated plan")
        for source in sources:
            p.asset(source, verify=True)
        with p.db() as db:
            latest = db.execute("SELECT MAX(id) FROM revisions").fetchone()[0]
            revision = (latest or 0) + 1
            directory = self.policy.write(p.root / "revisions" / str(revision) / "project.fcproj").parent
            target = directory / "project.fcproj"
            publish(native, target)
            atomic_json(directory / "plan.json", plan)
            atomic_json(directory / "provenance.json", {"pipeline": PIPELINE, "backend": self.config["filmcraft"], "validation": validation, "sources": {k: {"path": v["path"], "hash": v["hash"]} for k, v in sources.items()}, "audioProcessing": sound_results, "nativeInspection": inspection})
            db.execute("INSERT INTO revisions VALUES (?,?,?,?,?)", (revision, latest, json_text(plan), str(target), digest(target)))
        return {"revision": revision, "parent": latest, "nativeProject": str(target), "plan": str(directory / "plan.json"), "provenance": str(directory / "provenance.json"), "duration": validation["duration"], "originalsWritten": False}

    def revision(self, project, revision=None):
        p = self.project(project)
        with p.db() as db:
            row = db.execute("SELECT * FROM revisions WHERE id=?", (revision,)).fetchone() if revision is not None else db.execute("SELECT * FROM revisions ORDER BY id DESC LIMIT 1").fetchone()
        if row is None:
            raise ValueError("no editable revision exists; apply a validated timeline first")
        result = dict(row)
        result["plan"] = json.loads(result["plan"])
        path = self.policy.read(result["native_path"])
        if digest(path) != result["native_hash"]:
            raise ValueError("native project was modified outside this revision; import/edit it explicitly rather than silently overwriting history")
        return result

    def history(self, project):
        p = self.project(project)
        with p.db() as db:
            return {"revisions": [dict(r) for r in db.execute("SELECT id,parent,native_path,native_hash FROM revisions ORDER BY id DESC LIMIT 50")]}

    def render(self, project, output, preview=False, seconds="5", revision=None, replace=False):
        p = self.project(project)
        self.revision(project, revision)
        output_path = self.policy.write(p.root / "exports" / output)
        if not output_path.is_relative_to(p.root / "exports") or output_path.suffix.lower() != ".mp4":
            raise ValueError("exports must be .mp4 paths beneath this project's exports directory")
        if output_path.exists() and not replace:
            raise ValueError("output exists; choose a new name or explicitly authorize replacement")
        if rational(seconds) <= 0 or type(replace) is not bool:
            raise ValueError("preview duration/replacement flag is invalid")
        return self.jobs.submit(project, "render", {"output": str(output_path), "preview": preview, "seconds": seconds, "revision": revision, "replace": replace})

    def _render(self, project, args, job):
        p = self.project(project)
        r = self.revision(project, args.get("revision"))
        validation = p.validate(r["plan"])
        for asset in {r["asset"] for r in validation["ranges"]} | ({validation["audio"]["microphone"]} if "microphone" in validation["audio"] else set()):
            p.asset(asset, verify=True)
        work = self.policy.write(p.root / ".work" / job / "render.mp4").parent
        output = work / "render.mp4"
        argv = [self.config["filmcraft"], "--project", r["native_path"], "export", str(output), "--format", "h264"]
        expected = rational(validation["duration"])
        if args["preview"]:
            expected = min(expected, rational(args["seconds"]))
            argv += ["--start", "0", "--end", str(float(expected))]
        stdout, stderr = self.policy.run(argv, work, timeout=self.config.get("timeoutSeconds", 1200))
        atomic_json(work / "native-export-log.json", {"stdout": stdout[-8000:].decode("utf-8", "replace"), "stderr": stderr[-8000:].decode("utf-8", "replace")})
        qc = self.qc(p, output, expected, validation)
        atomic_json(work / "qc.json", qc)
        if not qc["passed"]:
            raise ValueError("deterministic export QC failed; prior output preserved. Inspect the job's qc.json and repair the edit explicitly.")
        target = self.policy.write(args["output"])
        publish(output, target, replace=args["replace"])
        return {"video": str(target), "revision": r["id"], "nativeProject": r["native_path"], "plan": str(Path(r["native_path"]).with_name("plan.json")),
                "provenance": str(Path(r["native_path"]).with_name("provenance.json")), "qc": qc, "qcPath": str(work / "qc.json"), "backend": "FilmCraft native H.264/AAC export", "originalsWritten": False}

    def qc(self, p, output, expected, validation):
        stdout, _ = self.policy.run([self.config["ffprobe"], "-v", "error", "-show_streams", "-show_format", "-of", "json", str(output)])
        metadata = json.loads(stdout)
        streams = metadata["streams"]
        videos = [s for s in streams if s["codec_type"] == "video"]
        audio = [s for s in streams if s["codec_type"] == "audio"]
        fps = rational(validation["output"]["fps"])
        failures = []
        if not videos or videos[0]["width"] != validation["output"]["width"] or videos[0]["height"] != validation["output"]["height"]:
            failures.append("missing/wrong-size video")
        if abs(Fraction(metadata["format"]["duration"]) - expected) > 2 / fps + Fraction(1, 20):
            failures.append("incorrect duration/truncation")
        if videos and videos[0]["codec_name"] != "h264":
            failures.append("unexpected video format")
        if videos and abs(Fraction(videos[0]["avg_frame_rate"]) - fps) > Fraction(1, 10000):
            failures.append("incorrect frame rate")
        if not audio:
            failures.append("missing audio")
        elif any(stream["codec_name"] != "aac" for stream in audio):
            failures.append("unexpected audio format")
        # Decode the entire tiny/selected output to catch corruption and truncation, not only headers.
        self.policy.run([self.config["ffmpeg"], "-nostdin", "-v", "error", "-xerror", "-err_detect", "explode", "-i", str(output), "-f", "null", "-"], timeout=self.config.get("timeoutSeconds", 1200))
        _, log = self.policy.run([self.config["ffmpeg"], "-nostdin", "-nostats", "-v", "info", "-i", str(output), "-vf", "blackdetect=d=0.1:pix_th=0.1", "-af", "astats=metadata=0:reset=0,silencedetect=noise=-45dB:d=0.3", "-f", "null", "-"], timeout=self.config.get("timeoutSeconds", 1200))
        text = log.decode("utf-8", "replace")
        peaks = re.findall(r"Peak level dB:\s*(-?\d+(?:\.\d+)?|-inf)", text)
        cut_checks = []
        # Bounded independent source/output pixel checks catch wrong clips/order without claiming semantic understanding.
        sample_cuts = validation["ranges"][:16] if videos else []
        for cut in sample_cuts:
            a, b = rational(cut["timelineIn"]), min(expected, rational(cut["timelineOut"]))
            if b <= a:
                continue
            position = (a + b) / 2
            source_time = rational(cut["in"]) + position - a
            source = p.asset(cut["asset"])
            dimensions = validation["output"]
            conform = f"scale={dimensions['width']}:{dimensions['height']}:force_original_aspect_ratio=decrease,pad={dimensions['width']}:{dimensions['height']}:(ow-iw)/2:(oh-ih)/2,scale=16:16"
            ref, _ = self.policy.run([self.config["ffmpeg"], "-nostdin", "-v", "error", "-ss", str(float(source_time)), "-i", source["path"], "-frames:v", "1", "-vf", conform, "-pix_fmt", "rgb24", "-f", "rawvideo", "-"])
            observed, _ = self.policy.run([self.config["ffmpeg"], "-nostdin", "-v", "error", "-ss", str(float(position)), "-i", str(output), "-frames:v", "1", "-vf", "scale=16:16", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"])
            error = sum(abs(x - y) for x, y in zip(ref, observed, strict=True)) / len(ref) if len(ref) == len(observed) == 16 * 16 * 3 else 255
            cut_checks.append({"asset": cut["asset"], "sourceSeconds": str(source_time), "outputSeconds": str(position), "meanAbsoluteRGBError": error, "threshold": 32})
            if error > 32:
                failures.append("representative source/output cut content differs (review codec/color/conform limitations)")
        edges = []
        for cut in validation["ranges"][1:17] if audio else []:
            boundary = rational(cut["timelineIn"])
            if boundary >= expected:
                continue
            raw, _ = self.policy.run([self.config["ffmpeg"], "-nostdin", "-v", "error", "-ss", str(float(max(Fraction(0), boundary - Fraction(1, 100)))), "-i", str(output), "-t", "0.02", "-vn", "-ac", "1", "-ar", "48000", "-f", "f32le", "-"])
            import array
            samples = array.array("f"); samples.frombytes(raw)
            delta = max((abs(samples[i + 1] - samples[i]) for i in range(len(samples) - 1)), default=0)
            edges.append({"boundarySeconds": str(boundary), "maxAdjacentSampleDelta": delta, "possibleAbruptEdge": delta > 0.25, "kind": "signal finding, not semantic judgment"})
        findings = {"blackIntervals": re.findall(r"black_start:[^\n]+", text)[:50], "silenceIntervals": re.findall(r"silence_(?:start|end):[^\n]+", text)[:50], "peakDbFS": peaks[-1:] or None,
                    "possibleClipping": bool(peaks and peaks[-1] != "-inf" and float(peaks[-1]) >= -0.01),
                    "interpretation": "black/silent intervals are findings, not automatic errors; cut order/content and abrupt audio edges require bounded boundary inspection"}
        return {"passed": not failures, "failures": failures, "expectedDuration": str(expected), "actualDuration": metadata["format"]["duration"], "streams": [{k: s[k] for k in ["codec_type", "codec_name", "width", "height", "avg_frame_rate", "sample_rate", "channels"] if k in s} for s in streams], "findings": findings, "representativeCutChecks": cut_checks, "audioBoundaryChecks": edges}

    def align(self, project, camera, microphone, max_lag="5"):
        p = self.project(project)
        for asset in [camera, microphone]:
            a = p.asset(asset)
            if not any(s["codec_type"] == "audio" for s in a["metadata"]["streams"]):
                raise ValueError("both alignment sources require a recorded audio stream")
        if not 0 < rational(max_lag) <= 10:
            raise ValueError("alignment lag search is bounded to 0..10 seconds")
        return self.jobs.submit(project, "align", {"camera": camera, "microphone": microphone, "maxLag": max_lag})

    def _align(self, project, args, job):
        import numpy as np
        p = self.project(project)
        work = self.policy.write(p.root / ".work" / job / "alignment.json").parent
        arrays = []
        for i, asset in enumerate([args["camera"], args["microphone"]]):
            source = p.asset(asset, verify=True)
            raw = work / f"sync-{i}.f32"
            self.policy.run([self.config["ffmpeg"], "-nostdin", "-v", "error", "-i", source["path"], "-t", "120", "-vn", "-ac", "1", "-ar", "4000", "-f", "f32le", str(raw)])
            values = np.fromfile(raw, dtype="<f4").astype(np.float64)
            if len(values) < 4000:
                raise ValueError("alignment requires at least one second of common audio")
            values -= np.mean(values)
            arrays.append(values)
        reference, mic = arrays
        n = 1 << (len(reference) + len(mic) - 1).bit_length()
        correlation = np.fft.irfft(np.fft.rfft(mic, n) * np.conj(np.fft.rfft(reference, n)), n)
        max_lag = int(rational(args["maxLag"]) * 4000)
        lags = np.arange(-max_lag, max_lag + 1)
        scores = correlation[lags % n] / max(float(np.linalg.norm(reference) * np.linalg.norm(mic)), 1e-12)
        best = int(np.argmax(scores)); lag = int(lags[best]); peak = float(scores[best])
        far = scores[np.abs(lags - lag) > 200]
        second = float(np.max(far)) if len(far) else 0.0
        if peak < 0.45 or peak - second < 0.08:
            raise ValueError("alignment is silent, ambiguous or lacks common audio; do not guess an offset")
        result = {"camera": args["camera"], "microphone": args["microphone"], "offsetSeconds": str(Fraction(lag, 4000)), "normalizedCorrelation": peak, "nextDistantPeak": second,
                  "method": "bounded 120-second mono 4 kHz waveform cross-correlation", "convention": "microphone source timestamp = camera source timestamp + offsetSeconds", "limits": "one recording pair, constant offset, no clock-drift correction or inferred lip sync"}
        atomic_json(work / "alignment.json", result)
        return result

    def worker(self, job):
        row = self.jobs.raw(job)
        if row["state"] != "running":
            raise ValueError("worker has no running queue reservation")
        try:
            args = json.loads(row["args"])
            handler = {"ingest": self._ingest, "analyze": self._analyze, "apply": self._apply, "render": self._render, "align": self._align}[row["operation"]]
            result = handler(row["project"], args, job)
            self.jobs.update(job, progress=1, state="done", result=result)
        except Exception as exc:
            self.jobs.update(job, state="failed", error=str(exc))
        finally:
            self.jobs.pump()
