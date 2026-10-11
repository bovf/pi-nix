# CLI and MCP workflow

The Home Manager wrapper supplies the declared read roots and separate derived write root. Otherwise supply `--config FILE` with `readRoots`, `writeRoot` and exact installed native `filmcraft`/`soundcraft` CLI paths. The package supplies pinned managed FFmpeg, CPU Whisper/model, Bash, Coreutils, Python/MCP and Bubblewrap. Use only Linux for this first slice.

```sh
badwater-video project create tutorial
badwater-video --wait ingest tutorial /authorized/raw/camera.mp4 /authorized/raw/mic.wav
badwater-video assets tutorial --limit 20
badwater-video analyze tutorial ASSET_ID
badwater-video jobs status JOB_ID
badwater-video search tutorial 'create the project'
badwater-video inspect tutorial ASSET_ID --at '3/2'
badwater-video --wait align tutorial CAMERA_ASSET_ID MIC_ASSET_ID --max-lag '5'
badwater-video timeline validate tutorial /derived/tutorial/plan.json
badwater-video --wait timeline apply tutorial /derived/tutorial/plan.json
badwater-video --wait preview tutorial --out preview-v1.mp4 --seconds '5'
badwater-video --wait export tutorial --out final-v1.mp4
badwater-video history tutorial
```

IDs above are placeholders: copy actual returned IDs, never invent native project IDs. `--wait` is an optional CLI-only bounded wait; MCP always returns durable job IDs for ingest/analysis/alignment/edit/export. Poll status from the caller with a bounded deadline, not an extension startup timer. `jobs cancel`/`jobs retry` operate on a single recorded job. Queued jobs are global to this write root and recover through later interaction after crashes.

Example plan structure (replace the IDs and ranges with measured authorized source ranges):

```json
{
  "version": 1,
  "output": {"width": 1280, "height": 720, "fps": "30000/1001", "aspect": "16/9"},
  "clips": [
    {"asset": "RETURNED_CAMERA_ID", "in": "1/2", "out": "9/2", "reason": "Show the authorized required demonstration"},
    {"asset": "RETURNED_CAMERA_ID", "in": "15/2", "out": "21/2", "reason": "Retain the conclusion; omit the excluded retry"}
  ],
  "constraints": {
    "targetDuration": "7", "tolerance": "1001/30000", "maxCutSeconds": "4",
    "mustInclude": [{"asset": "RETURNED_CAMERA_ID", "in": "1", "out": "2"}],
    "mustExclude": [{"asset": "RETURNED_CAMERA_ID", "in": "5", "out": "7"}]
  },
  "audio": {"microphone": "RETURNED_MIC_ID", "offset": "MEASURED_OFFSET", "normalize": true}
}
```

Times are half-open source-second intervals; placement uses native ticks, rounded within half a tick. Stream timebases/nominal/average rates are retained, not replaced with an assumed constant frame index. A microphone clock timestamp is `camera timestamp + offset`. First-slice microphone replacement supports one camera recording at a time; no inferred drift/multicamera sync. Sound normalization is explicit mono speech leveling toward -16 LUFS, constrained by a -1 dB true-peak ceiling and a 20 dB gain cap. It processes selected cuts of at most 120 seconds in the native audio engine, not a full recording in RAM.

The index is versioned SQLite/WAL with full streaming SHA-256 input identities. Cached analysis is keyed by input hash, pipeline, pinned model, FFmpeg/Whisper and relevant options. Reuse validates original bytes in a worker; modified/missing originals are refused until explicitly re-ingested. Transcript search is literal FTS5 phrase matching, not embeddings/semantic retrieval. Observation queries cap windows at 120 seconds and results at 20. ASR uses sequential 30-second, mono 16 kHz windows; frames are bounded sparse/scene-neighborhood samples, not exhaustive visual understanding.

Original roots and derived root must be disjoint. Children see only a read-only store, declared read-only raw roots, the derived write root, private HOME/tmp/dev/proc and no network/host sockets. Traversal/symlinks/linked-output replacement are refused, filenames are argv/JSON data, and successful outputs are published atomically only after QC. Logs remain local and are bounded in model-facing responses. Silent/ambiguous alignment is refused. Missing sources/corrupt media/unknown plans/non-finite times/unsafe paths/unsupported backends fail visibly.

Final QC decodes the output and checks dimensions/rate/codec/duration/audio; reports clipping, black/silent intervals for review. Captions, automatic music/effects/generative assets, diarization, semantic search and cross-editor project exports are not implemented/default-enabled. Inspect cut order and audiovisual meaning against the user goal; a header probe alone is not acceptance.
