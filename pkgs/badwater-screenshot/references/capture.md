# Capture modes and limits

All calls use `badwater-screenshot` through Pi's sole builtin MCP owner. Backend
commands/libraries are Nix-managed; no shell command string, installer or custom
CDP/profile attachment is accepted. GUI support is Linux/Niri or KDE Plasma 6.

| Kind | Explicit target | Behavior |
|---|---|---|
| `web` | `url`, optional authorized `allow_origins` | Fresh isolated Chromium desktop/mobile PNGs and private browser report; GET/HEAD exact-origin mediation, no focus/cookies/CDP |
| `code` | absolute `repo`, relative `file`, `start_line`/`end_line` | Escaped source text, at most 40 lines, in isolated Chromium; source hash recorded; viewport may wrap/clip long lines |
| `window` / Niri | numeric `window_id` | Captures that window without focusing; native Niri also replaces clipboard, requiring explicit opt-in |
| `window` / KDE | `{uuid}` `window_id` | Spectacle background capture; an unfocused target needs explicit focus opt-in and restoration |
| `screen` / Niri | output name from authorized discovery | grim output capture, no clipboard/focus change |
| `screen` / KDE | `output: all` or `current` | Spectacle desktop/current-monitor capture; request that precise scope |
| `region` | Niri `[x,y,width,height]` | grim region only; KDE geometry capture fails rather than snapshotting a broader desktop |

`backend: auto` uses session environment only when a GUI tool is invoked. An
SSH session without GUI access fails clearly; headless URL/code is still usable.
Web URLs with credentials, queries or fragments are rejected; use an authorized
GUI window for existing application state. Do not enable extra origins merely
to bypass a failed network request.

KDE capture records original window/desktop before a focus transaction and uses
finally for normal success/failure restoration. If the human changed focus, it
does not steal focus back. Hard process kills/window closure can defeat restore;
private `focus-before.json` retains the original target for manual recovery.
GUI capture transactions are file-locked to avoid concurrent focus races. No WM
settings, focus rules or window desktop membership are changed.

Artifacts live in `${XDG_STATE_HOME:-~/.local/state}/badwater-screenshot/captures/<id>/`.
Directories are `0700`, files `0600`; final PNGs are re-encoded without source metadata.
Receipts record backend, exact target, capture time, dimensions and SHA256.
Nothing cleans up or publishes them automatically. A failed attempt may retain
private error/partial artifacts, never a success claim.

`screenshot_read_capture` accepts only a stored capture ID and listed image name
(`desktop`/`mobile` for web/code, `capture` for GUI). It checks unchanged bytes.
Default returns metadata only. Sharing requires explicit image-input permission;
an optional crop is `[x,y,width,height]` in the original image. Share smaller
relevant images; the model-sharing payload is limited to 10 MiB. No arbitrary file
reader, recursive screen recording, OCR or automatic document export is supplied.
