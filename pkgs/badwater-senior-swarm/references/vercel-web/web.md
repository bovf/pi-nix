# Web interface reference — adapted from Vercel Labs

[Vercel Web Interface Guidelines](https://github.com/vercel-labs/web-interface-guidelines/blob/434b7f91364665f2f733b310ec54809bf8f37937/command.md),
Copyright (c) 2025 Vercel Labs, MIT; see LICENSE and ../sources.json.
Modified: condensed static reference instead of upstream latest-source fetching.

- Use semantic buttons for actions and anchors for navigation. Icon-only buttons
  need accessible names; inputs need labels, correct types and suitable
  autocomplete. Decorative imagery should be hidden from assistive technology;
  meaningful imagery/media needs descriptions/captions where applicable.
- Preserve visible keyboard focus. Sticky overlays must not hide the focused
  element. Headings, landmarks, skip navigation and focus order should express
  the task structure. Async status changes need appropriate live announcements.
- Forms must allow paste, associate labels and errors, expose pending submission
  clearly and support correction without losing input. Protect unsaved changes.
- Honor reduced motion; animations should be interruptible and primarily use
  transform/opacity. Avoid `transition: all`. Long autoplay needs pause/stop.
- Handle empty, short, long and localized content. Flex/grid children should
  shrink/wrap without losing meaningful text. Respect zoom, touch and responsive
  layouts; do not treat one desktop screenshot as mobile acceptance.
- Reserve image dimensions to prevent layout shift, defer below-fold imagery,
  and prioritize the actual critical image. Batch layout reads/writes and keep
  per-keystroke form work cheap. Large lists may need windowing; measure first.

Return concise location-backed findings with impact and acceptance evidence.
Style preferences are not accessibility failures. Source review plus axe cannot
certify complete WCAG compliance, keyboard behavior or subjective quality.
No live guideline fetch, installer, browser attachment or deployment is part of
this guide. Only approved private browser evidence may be gathered by the parent.
