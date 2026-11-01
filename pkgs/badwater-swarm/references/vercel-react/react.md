# React/Next.js reference — adapted from Vercel Engineering

[Vercel agent-skills](https://github.com/vercel-labs/agent-skills/tree/1a2c79d4e6c4a2283dc2c614b6538cbe1ed5ca62),
MIT as declared in retained UPSTREAM-SKILL.md; source paths/hashes in
../sources.json. This is a small modified selection, not all upstream rules.
The five `rules/*.md` examples are unmodified source references, not installed
skills. Apply only when the actual project framework/version supports them.

Prioritize measured critical paths before micro-optimizations:

1. Eliminate unnecessary waterfalls: start independent operations concurrently,
   defer awaiting until needed, and restructure component/data dependencies.
   Preserve ordering and authorization dependencies; Promise.all is not a reason
   to parallelize mutations or unbounded requests.
2. Reduce bundle cost: import narrowly, dynamically load genuinely heavy optional
   components, and avoid eagerly loading third parties before needed. Measure
   real build/runtime effects instead of reporting hypothetical savings.
3. Treat server actions as public endpoints. Authenticate and authorize inside
   the action, validate input, and never rely on hidden UI as an access control.
4. Keep request data isolated; do not store per-user mutable state globally.
   Deduplicate request-local work and minimize client serialization without
   sharing sensitive cache entries across users.
5. Optimize subscription/render work only when relevant: derive state directly,
   use functional updates and stable dependencies; avoid needless memoization.

Evidence must name source locations, framework assumptions, observed cost or
correctness issue, and the approved command/fixture proving the improvement.
No deployment, tokens, remote benchmark, runtime dependency install or external
service call is authorized. The parent decides whether verification may execute.
