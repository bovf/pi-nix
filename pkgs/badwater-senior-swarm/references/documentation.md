# Librarian: maintainable, source-grounded documentation

Locally authored workflow guidance; repository instructions take precedence.
No installer, generator or external service is required.

## Verify before writing

- Read the implementation, public entry points, configuration and nearby tests.
  Use supplied execution receipts only for the exact revision/scope they prove.
- Trace each changed command, option, path, default and behavioral claim to that
  evidence. Do not invent setup steps, APIs, guarantees, examples or test passes.
- Distinguish supported behavior, proposals, historical receipts and unknowns.
  Ask about material business/product decisions instead of filling them in.
- Review documentation on every change. Write only when it helps a reader or
  corrects verified drift; no finding quotas, mandatory new pages or churn.

## Organize for the reader

- Keep README a concise entry point: purpose, supported quick start, essential
  usage and links. Put detailed material in focused, descriptively named docs/
  pages only when it is useful enough to maintain separately.
- Separate tutorials, task-oriented how-to, reference and explanation where that
  helps navigation; do not create empty category trees to follow a template.
- Give each fact one authoritative home. Link instead of copying large command,
  option or architecture lists. Preserve useful anchors or update their callers.
- Use descriptive headings, short paragraphs, direct language and small examples.
  Keep warnings next to risky operations; do not trade safety for a shorter page.
- Split long mixed-purpose pages at real topic boundaries. Remove obsolete or
  duplicated guidance; Git already preserves history. Avoid arbitrary word caps,
  speculative roadmaps, chat transcripts, repeated summaries and release diaries.

## Close the loop

- Cover approved new/changed user behavior, configuration, compatibility limits
  and recovery only where relevant. Read the actual final code after upstream
  tasks/repairs; do not document the initial plan as if it were implemented.
- Check relative paths, links/anchors, navigation, commands/options and examples
  against the repository. Use existing declared checks; never install tools or
  claim a manual link inspection was a lint/build/runtime test.
- Exactly `git diff --check` is available as a bounded whitespace check when no
  project doc check exists. It covers tracked working-tree differences, not new
  untracked files, links, factual accuracy or UI; inspect new pages explicitly.
- Fresh read-only Librarian review compares the integrated HEAD with source and
  approved scope. Missing/out-of-scope documentation blocks for a new approval,
  not a hidden extra edit. Report real coverage and unverified behavior plainly.
