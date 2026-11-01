# Badwater Screenshot

`badwater-screenshot` is a Linux stdio MCP and explicit Pi skill. It adds no
startup Pi extension, browser profile attachment, WM setting or credential owner.
The server starts passively; GUI discovery, capture, focus/clipboard effects,
model sharing and publication each need operator-approved scope.

## Tools

- `screenshot_capabilities`: backend/limit information only; no desktop query.
- `screenshot_targets`: authorized Niri/KDE target IDs, optional PID filter.
  Titles are omitted by default. Do not enumerate private windows implicitly.
- `screenshot_capture`: explicit `web`, `code`, `window`, `screen` or `region`.
  Returns private artifact metadata, not pixels.
- `screenshot_read_capture`: metadata by default. Only explicit
  `share_with_model=true` returns a selected PNG, optionally cropped, after image
  input capability and data-sharing consent are checked.

Start with `/skill:badwater-screenshot <approved capture task>` and its
[mode reference](../pkgs/badwater-screenshot/references/capture.md).
Headless web/code uses the existing isolated Chromium/origin-mediation helper,
not personal cookies/CDP. A fresh render is not an existing authenticated tab.
Code mode renders at most 40 escaped source lines and records the source hash;
viewport clipping is a gap, and the image does not prove code executed.

## GUI focus and privacy

Niri can capture an unfocused window by explicit ID without activation, but its
native API also sets the clipboard: opt in separately or use no-clipboard
output/region/headless capture. KDE uses Spectacle background/new-instance mode.
An unfocused window requires `allow_focus=true`; the original window/desktop is
saved, then restored in finally after normal success/failure. User focus changes
are respected rather than overridden. Hard kills/closed windows can defeat
restoration; private `focus-before.json` supports manual recovery.

Niri regions use grim directly. KDE noninteractive coordinate regions fail
rather than first capturing a broader desktop. No focus-follows/new-window policy,
window membership, shortcuts or compositor settings are changed. GUI operations
are file-locked; headless operation needs no visible window or GUI session.

## Evidence and validation

Captures live under `$XDG_STATE_HOME/badwater-screenshot/captures/<id>` (fallback
`~/.local/state`). Directories `0700` / files `0600`, re-encoded PNGs, source/target/time/
SHA/dimension receipts, no automatic cleanup or export. No arbitrary command or
image-file reader is exposed. Publishing a capture needs approved documentation
paths and pixel-content permission. The Librarian can consume parent-provided
captures; its PNG assets are scoped and bounded, not ambient desktop authority.

The package uses Nix Python MCP/Pillow and managed Niri/grim/Spectacle/kdotool.
MCP 1/2 import compatibility uses the single packaged SDK, not a runtime install.
Tests cover 10 backend cases, native Pi stdio/skill/sharing lifecycle and synthetic
isolated Chromium web/code captures. GUI command/focus behavior uses controlled
fixtures and offline pinned CLI/API inspection—not a real personal-desktop
acceptance claim. Real KDE/Niri GUI/device behavior remains a manual gate.
