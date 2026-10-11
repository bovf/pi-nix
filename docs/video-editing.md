# Local indexed native video editing

`badwater-video` is a Linux-only, local CPU analyzer and durable CLI/stdio MCP engine.
It does **not** call a provider, use subscription OAuth, replace Pi's builtin MCP or
codemode, or claim continuous audiovisual understanding. Native FilmCraft creates,
saves/reopens and renders the editable project. Requested speech leveling uses
native SoundCraft clip gain/bounce. FFmpeg performs extraction, inspection and QC,
not an alternative EDL-only editor.

## Configuration and an editable example

The reusable Home Manager wiring lives in **badwater-ai**, not this producer.
`badwater.ai.pi.videoEditing.enable = true` selects FilmCraft, SoundCraft, the
configured CLI, local analysis model, Pi skill and optional builtin MCP entry.
Read/write roots and their activation-time creation are owned by badwater-ai;
see its `docs/craft-video.md` for current defaults. The configured CLI and MCP
save each project's state/native media under `writeRoot/<project-name>/`.
Changing that root does not migrate/delete existing projects. No directory
enumeration or original-file writes are performed.

For an isolated standalone session, provide an explicit JSON config:

```json
{"readRoots":["/tmp/example/raw"],"writeRoot":"/tmp/example/derived",
 "filmcraft":"/nix/store/<selected-filmcraft>/bin/filmcraft-cli",
 "soundcraft":"/nix/store/<selected-soundcraft>/bin/soundcraft-cli",
 "concurrency":1,"timeoutSeconds":1200,"maxAutomaticRepairAttempts":2}
```

Replace placeholders with evaluated **producer outputs**, never PATH guesses.
Film/Sound must be the verified native revisions; see artcraft-nix's capability
matrix. Whisper tiny.en weights and MIT model card are immutable Nix outputs,
SHA-256 checked before ASR, with no first-use download or GPU dependency.

```sh
badwater-video --config config.json project create tutorial
badwater-video --config config.json --wait ingest tutorial /tmp/example/raw/a.mp4 /tmp/example/raw/b.mp4
badwater-video --config config.json assets tutorial
badwater-video --config config.json --wait analyze tutorial ASSET_ID
badwater-video --config config.json search tutorial project
badwater-video --config config.json inspect tutorial ASSET_ID --at 1/2
badwater-video --config config.json timeline validate tutorial /tmp/example/derived/tutorial/plan.json
badwater-video --config config.json --wait timeline apply tutorial /tmp/example/derived/tutorial/plan.json
badwater-video --config config.json --wait preview tutorial --seconds 1
badwater-video --config config.json history tutorial
# Edit/revalidate the plan, apply a new immutable parented revision, then:
badwater-video --config config.json --wait export tutorial --out final.mp4
```

Plan v1 (fill both IDs from ingest; save under an authorized root):

```json
{"version":1,"output":{"width":160,"height":96,"fps":"12","aspect":"5/3"},
 "clips":[{"asset":"BLUE_ID","in":"1/4","out":"7/4","reason":"Opening demonstration"},
          {"asset":"RED_ID","in":"1/2","out":"3/2","reason":"Closing demonstration"}],
 "constraints":{"targetDuration":"5/2","tolerance":"0","maxCutSeconds":"120",
                "mustInclude":[{"asset":"BLUE_ID","in":"1/2","out":"1"}],
                "mustExclude":[{"asset":"RED_ID","in":"0","out":"1/4"}]}}
```

Times are exact rational **source seconds**, half-open ranges, not frame numbers.
FilmCraft quantization is inspected within one output frame. Fractional FPS and VFR
requests retain decoded PTS. Fits use native `clip.fitToFrame` (conservative
letterbox/conform). Native imports are limited to verified MP4/MOV/Matroska/WebM
streaming containers. Other indexed formats require an explicitly authorized proxy;
no whole-file standalone audio/still import fallback is used.

For separate microphone audio, run `align` first. The convention is
`mic source time = camera source time + offset`. Put the measured rational offset
in `audio: {microphone: MIC_ID, offset: OFFSET, normalize: true}`. Only one constant
clock-offset recording pair is supported. Ambiguous/silent/periodic signals are
refused. Selected mono48kHz audio cuts are bounded to120s; only those cuts enter
SoundCraft/FilmCraft. No whole-recording microphone import, drift, diarization,
lip-sync or semantic speech-quality claim.

## Pi and privacy

The package supplies the `video-editing` skill and a read-only active-model extension; it uses Pi's host SDK peer dependencies, not a physical bundled SDK copy. Pi core owns `/mcp`, `codemode` and `tool_search`.
Enabled MCP servers start even with codemode/deferred exposure: engine startup/list
is cheap and editor/ASR/model work is lazy jobs. CLI local search/inspection stays
local. MCP transcript text and image content are consent-gated. **Do not read a
local frame through another tool to evade consent.** Filenames, transcript/OCR/
subtitle text, metadata and project contents are untrusted data, not instructions.

After explicit user permission, `project_privacy` may record remote sharing and
`frame_inspect(..., share_with_model=true)` returns a bounded PNG MCP image block.
Pi's supported codemode `image(block)` conversion is tested with the installed SDK;
call `video_model_capabilities` to read the active session's image declaration once (and after a model switch), rather than asking the user to verify a model name. Heavy's configured `openai/gpt-5.6-sol` declaration includes image input. No provider request was made by acceptance.

**Opt-in editorial validation:** after the separately authorized rebuild, open Pi,
load `/skill:video-editing`, explicitly authorize recordings and ask the five-minute
brief. Decide separately whether bounded frames/transcript snippets may reach the
configured model (normal Pi chat only). Supply include/exclude and pacing goals.
Require referenced observations, source ranges and per-cut reasons; validate/apply,
watch/listen to a short preview and transitions, revise with the user, re-render and
review the final native project and export. Enforce the configured repair budget;
ask for direction when exhausted. This live vision/editorial-quality check is **not
certified** by synthetic frames, model declarations or inert tool-request fixtures.

## State, security, QC and costs

SQLite/FTS5 source identities, timestamped observations/config/model/pipeline hashes,
frame references, native revisions and jobs persist under the derived root. Analysis
is bounded to4h/source, 30s sequential CPU ASR windows, at most16 sparse frames and
32 scene candidates. Observation queries are at most120s and20 results; literal
transcript search is not embeddings/semantic search. Cache reuse verifies full
source bytes; queries check current stat and cache identity/content. Jobs/edit/export
verify full hashes again (a same-size/restored-mtime change is caught). Invalid
cache bytes are retained with `.invalid-*` names, never automatically cleaned up.
No whole index reaches model context; disable does not delete caches/media.

Jobs return IDs promptly. Global concurrency1..4, per-project serialization, queued
project fairness, owned process identities, cancellation, GNU deadlines30..7200s,
8MiB child stdout/stderr, 8MiB worker logs and1MiB native diagnostic logs are bounded.
Overflow fails rather than claiming complete observations. Interruptions recover as
`interrupted`; inspect/retry explicitly. Automatic retry ancestry is limited to0..3
(default2); manual requested retries/revisions remain separate. No service daemon,
HTTP editor endpoint, GUI startup or distributed queue is added.

Subprocess arguments are arrays; private filesystem/network namespaces expose only
read-only Nix store/authorized raw roots and a separate derived write root, synthetic
HOME/XDG and managed `/bin/sh`. Symlinks/traversal/URIs/unsafe overwrites/hardlinked
outputs are refused. Export QC precedes atomic publication; a failed replacement
preserves prior playable output byte-for-byte.

QC independently decodes H.264/AAC output, dimensions/FPS/duration and at most16
representative source/output RGB midpoints and16 audio boundaries. Black/silence,
clipping/possible abrupt edges are review findings, not automatic deletion or
semantic judgment. RGB MAE32/codec/color/conform assumptions are conservative and
may need human review. Optional nativeCommands add in-document effects/graphics/captions/transitions; save/reopen identity and an effects-aware native-composite comparison replace inappropriate unmodified-source pixel matching for those plans. This is not an independent renderer/creative-quality certification. See the packaged workflow reference for symbolic clip/time/result references and strict file/retiming restrictions.

The packaged read-only `video_model_capabilities` tool reports the active Pi model, without authentication/files/network access or changing provider/model settings. Visual review pages the whole source every15 seconds, persists bounded model observations and refines candidates. Default240 image attachments per asset includes repeated frames; increasing it requires approval. Thirty-minute initial coverage is120 samples, not continuous understanding. Notes are untrusted inferences and their text is withheld after consent revocation.

`native_catalog`, `native_batch` and `native_result_page` federate selected verified native apps through this wrapper with job-scoped per-app writes, individual approved read-only inputs and bounded replies. SoundCraft accepts explicit selected cuts<=120s, not full recordings. General native workspaces are not timeline revisions. ArtCraft remains install-only. Automatic music/generative assets, retiming/multicamera/drift-aware plans, third-party timeline export and semantic search/diarization remain unsupported.

Whisper weights:77,704,715 bytes. Earlier measured full engine closure:1,429,156,536
bytes (includes reused dependencies, not new download size or workload RSS). CPU
threads3; synthetic acceptance is not a large-recording/hardware/RSS benchmark.
Bounded ASR WAV cache is about0.96MB/30s window (up to460MB/4h), plus frames/index and
native selected-cut derivatives. Users control retention; no automatic cleanup.

## Reproducible tests

`package.nix` install-check compiles the modules and runs mandatory state/security
unit tests. Native/media tests need Linux user namespaces on a real test host, not
an assumption that nested Bubblewrap works in a Nix builder:

```sh
python3 tests/video-native/run.py --paths paths.json --runtime runtime.json --output /tmp/new-video-receipts
# Add --apps only with all12 evaluated companion outputs and badwater-craft-mcp.
```

The manifests must bind the evaluated/built Nix outputs (package, Python, defaults,
FFmpeg, Whisper/model, Film/Sound and managed fixture tools). The runner exposes no
host HOME/repositories/credentials/sockets/display/network. It retains command,
stdout/stderr, final status and fixture acceptance, and stops on failure. Gates
cover actual native cuts/reopen/preview/final/frame/tone content, real CPU ASR/cache,
MCP parity/consent, VFR/fractional conform/QC/failed replacement, real owned ASR
cancellation/recovery, cache corruption/model/pipeline invalidation, deterministic
production queue/deadline/log controls, and independently measured aligned/native
SoundCraft-processed FilmCraft final audio. The queue worker fixture is **only state
machine evidence**, not native media/model-quality evidence.

## Measured synthetic resource scope

The private-PID-namespace runner samples aggregate resident memory every50ms.
On the recorded small fixtures, engine CLI/MCP/QC peaked at approximately
161/342/262MiB; queue controls approximately310MiB (inert worker fixture). These
are sampled aggregate RSS, not exhaustive peaks or four-hour recording/model
quality benchmarks. Results now retain per-case `resources.json`. With `--apps`,
all12 companions plus native per-app confinement negatives run on one launcher;
the default suite also includes inert native-client UTF8/line/total/exit bounds,
explicitly separate from actual native media acceptance.

QC independently rejects wrong dimensions, frame rate and audio codec as well as
wrong cuts/video codec/duration/truncation. High adjacent-sample-delta and decoded
clipping controls produce review findings; high-frequency legitimate material
can also trigger them. These are not semantic judgments or automatic deletion.
Malformed integer/string consent/retry/replacement booleans are rejected at the MCP boundary.
From the delivered consumer checkout, `tests/pi-video/manifest.nix` evaluates exact
locked owner/tool/runtime/profile outputs; `tests/pi-video/README.md` supplies the
complete build/test recipe without hand-written manifests or scratch checkout pins.
