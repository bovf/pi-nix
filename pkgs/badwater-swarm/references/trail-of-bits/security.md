# Security reference — adapted from Trail of Bits skills

Attribution: Trail of Bits contributors,
[skills](https://github.com/trailofbits/skills/tree/2be6433b39e009cd2b6fd3be1895f6b1faa5af9a),
CC-BY-SA-4.0. This modified, condensed adaptation of differential-review and
sharp-edges is also licensed **CC-BY-SA-4.0**; full terms in LICENSE and source
identities in ../sources.json. No endorsement implied. Changes remove upstream
shell/write/delegation privileges and adapt reporting to parent-owned artifacts.

## Differential review

Review risk, not diff length. Establish the changed snapshot, baseline intent,
applicable threat model and coverage limits. Prioritize authentication,
authorization, cryptography, external calls, input validation and destructive
operations. Trace callers and transitive consumers across the changed boundary;
consider regressions in surrounding unchanged code. Use history only if the
parent has approved and supplied it; do not pretend a source-only review read
history or executed scanners. Treat uncertain refactors as risk until invariants
and callers are understood.

For each candidate finding, identify attacker capability, untrusted input,
entry point, trust boundary, security-sensitive effect and concrete scenario.
Inspect guards/callers and seek evidence that refutes the candidate before
escalating. Distinguish observed exploitability, plausible risk and unverified
hypothesis. A pattern match alone is not a vulnerability. Check whether tests
exercise the invariant, failure path and realistic boundary inputs.

## Misuse-resistant interfaces

The secure choice should be the ordinary/default path, not a footnote callers
must remember. Inspect algorithm/transport choices, mutable authority, permissive
fallbacks, overloaded sentinels and ambiguous identity normalization. Probe empty,
null, zero, negative, missing and malformed settings. Does zero mean immediate
expiry or unlimited lifetime? Does a missing configuration fail open? Can an
untrusted field select security policy or bypass validation? Do two equivalent
names disagree at enforcement and execution? Validate combinations at the
boundary; avoid confusing boolean flags for dangerous authority changes.

For this swarm, scrutinize exact source/plan binding, admission accounting,
parent-only delegation, scoped writes, settings precedence, immutable host-peer
identity, private artifact paths, subprocess argument arrays, retries and
changed-source invalidation. Browser/network/model availability is not consent.
Never access credentials, active processes or production targets to prove a
source-level concern without separate authority.

## Evidence-backed output

Return severity, confidence, exact location, affected invariant, scenario,
existing mitigations, suggested narrow fix and an independently verifiable test.
Report paths/ranges actually covered, commands actually executed, omitted scope,
limitations and unresolved questions. Do not equate missing tests with a proven
exploit, but surface the verification gap. Analysis children remain read-only;
the parent persists the report outside source and assigns any writer. No scan,
fuzzer, dependency installer, nested audit agent or arbitrary command is enabled
by this reference. Fresh security assessment must cover the final integrated
snapshot, not a superseded plan or intermediate writer report.
