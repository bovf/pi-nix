---
name: badwater-screenshot
description: Permission-first screenshots for fact checking, focused documentation images and authorized visual evidence. Prefer isolated headless web/code; use explicit GUI targets without changing WM policy.
disable-model-invocation: true
license: MIT
---

# Badwater Screenshot

Use only for operator-approved targets, data scope and purpose. Installing the
MCP does not authorize inspecting windows, capturing a personal desktop, changing
focus/clipboard, sharing pixels with a model or publishing an image.

## Choose the least intrusive capture

1. Read `screenshot_capabilities` and [capture modes](../../references/capture.md).
2. Prefer headless `web` for an explicit authorized URL, or `code` for a short
   source range. It uses a fresh isolated Chromium profile: no focus change,
   personal browser/CDP/cookies or implicit authenticated state. Numeric loopback
   is the default; extra exact origins require explicit network authorization.
3. For an existing GUI/browser state, ask for the target/data permission, then
   discover minimal IDs with `screenshot_targets` (filter by PID when possible;
   titles are omitted unless requested). Pass an exact window ID or screen/
   region, never assume the last opened app gained focus.
4. GUI focus is off by default. KDE can temporarily focus an explicit window only
   with `allow_focus=true` and restores the prior window/desktop in finally.
   Respect user intervention; never change WM focus settings. Niri can capture
   an unfocused window by ID, but its native API also changes the clipboard:
   require separate `allow_clipboard_change=true`, or choose a no-clipboard mode.
5. Capture returns private paths/provenance, not image bytes. Inspect metadata;
   verify the exact requested target/ref/URL/range and any focus warning. Unknown
   backends, failures and missing permissions are gaps, not broader fallbacks.

## Fact check and document

Before `screenshot_read_capture`, verify the active model declares image input
(use `video_model_capabilities` when available; do not guess from its name) and
obtain permission for the selected pixels to reach that model. Only then set
`share_with_model=true`; prefer an explicit crop to minimize unrelated content.
Metadata-only default does not share pixels. Never auto-OCR a private screen.

Use the original capture SHA/time/backend/target and current source/version in
claims. A headless render is not the user's existing tab; source-text rendering
is not proof code ran. A screenshot cannot establish hidden behavior or test passes.
Use readable crops, normal UI scale, useful alt text and short factual captions.
Do not fabricate UI/data or crop away a relevant warning to make docs attractive.
Capture receipts may contain private metadata: do not publish them automatically.

Publishing/copying PNGs into docs needs explicit approved paths and image-content
permission. Swarm code/docs tasks remain isolated and human-approved; the parent
can capture permitted evidence and hand paths to the Librarian without granting
it ambient desktop/network tools. Keep README short and link focused docs/assets.
No capture, focus/clipboard change or image sharing occurs merely on MCP startup.
