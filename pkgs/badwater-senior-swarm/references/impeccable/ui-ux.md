# UI/UX reference — adapted from Impeccable

Source: Paul Bakaus's [Impeccable](https://github.com/pbakaus/impeccable/tree/4f956490f0056ae1ff5ea80372cf56e83c001d3c),
Apache-2.0; see LICENSE, NOTICE.md and ../sources.json. Modified: condensed from
audit, critique, layout, harden and polish; raw workflow/delegation/CDP and live
injection instructions are not shipped or authorized. No upstream detector runs.

## Establish the product and design system

Identify the user's primary task, representative persona, target surface and
quality bar. Read existing DESIGN.md, tokens, shared controls and adjacent flows.
Preserve the incumbent visual language. Separate a local defect from missing
shared tokens, duplication or a conceptual mismatch. Do not smuggle a redesign
into polish or substitute a generic card/grid template for product intent.

Judge the design on its own before seeing mechanical accessibility results.
If independent assessments are appropriate, the parent alone arranges them;
children do not spawn workers or silently replace failed isolation with inline
review. Report unavailable evidence and stop on infrastructure failure.

## Inspect the whole task path

- Hierarchy: can a blurred view still reveal the primary action, secondary
  elements and meaningful groups? Use proximity, deliberate spacing rhythm and
  appropriate density before decorative containers.
- Responsive structure: narrow, intermediate and wide widths; DOM/focus order
  must agree with visual order after reflow. Check overflow, sticky layers,
  localization expansion, zoom, long content and empty states.
- Controls: semantic roles, labels, visible focus, keyboard order, meaningful
  status feedback and usable touch targets. Prefer approximately 44px targets;
  WCAG 2.5.8's 24px minimum has specific spacing and other exceptions, not a
  blanket 44px compliance requirement.
- Color/type: semantic design tokens, readable measure, consistent hierarchy,
  state and theme contrast. Test actual rendering rather than trusting tokens.
- Motion: interruptible, useful state feedback; honor reduced motion without
  destroying essential feedback. Avoid gratuitous layout/blur animation.
- Resilience: loading, empty, error, success, disabled, offline, slow and
  permission-limited states; long translations, RTL, emoji and missing content.

## Prioritize and report

Fix blocked tasks, data loss, misleading states and inaccessible paths first;
then missing states, structural inconsistency and only then cosmetic drift.
Prefer the narrowest correct shared component/token fix without speculative
system-building. Capture source locations, affected users, reproduction,
severity/confidence and actionable acceptance criteria. Record strengths and
uncertainty alongside defects. Do not infer design quality from detector scores.

Browser evidence requires explicit authorization and the packaged finite helper,
never an existing profile/CDP tab, cookies or authenticated session. Its desktop
1440x900 and mobile-emulated 390x844 captures plus axe are bounded evidence only:
not physical-device/touch, keyboard journey, all themes/states, native apps,
contrast in every state, performance or complete accessibility certification.
Additional interactions/viewports need a separately approved verification plan.
Keep subjective design judgment separate from observed mechanical violations.
