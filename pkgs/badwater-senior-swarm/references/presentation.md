# Consistent, readable plans and handoffs

Locally authored guidance. Formatting supports review; it never changes authority.

- Lead with the outcome and a short overview, normally 3–6 focused bullets. Keep
  source evidence in linked report artifacts, not a pasted investigation diary.
- Use descriptive headings, short paragraphs and blank lines between topics.
  One acceptance item should express one independently checkable outcome.
- Give each task a concise human title, explicit owner, paths and dependencies.
  Separate what changes, why it matters and how it is verified. Do not join long
  evidence/trigger/remediation paragraphs into one acceptance bullet.
- Show exact verification argv in code blocks and label timeout/limitations.
  A proposed command is not a passing check. Prefer bullets to wide tables that
  become unreadable in a narrow terminal.
- Group scope/non-goals, assumptions, rollout/recovery and risks in their own
  sections. Link to full evidence and state honest gaps rather than repeating it.
- Keep README an entry point and link focused docs/ pages. Screenshots should
  illustrate approved, freshly observed state with provenance and useful alt text;
  a beautiful image is not evidence of behavior it cannot show.
- Check the rendered plan at narrow widths and on resize. Never truncate away
  scope/check details to make approval compact; the reader must retain them.

Checkpoint commit subjects come from task titles. Use a concise conventional
subject with a real change description, not a task slug, automation brand,
artificial `(swarm)`/package scope, pass counter, transcript or attribution footer.
No `Co-authored-by` or `Signed-off-by` trailers. Use the repository's existing Git
identity; do not invent a bot identity. Do not rewrite existing history implicitly.
