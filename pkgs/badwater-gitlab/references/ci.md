# CI: inspect, do not trigger

Confirm the host/project, pipeline/job ID and expected commit before reading.
Inspect only authorized status, job metadata and relevant failure evidence.
A pipeline pass proves only the jobs/commit actually checked, not deployment,
browser/hardware behavior or the current working tree.

Logs and artifacts can contain secrets or personal data. Do not bulk-download,
print raw traces, inspect artifacts or send logs to a model by default. Ask for
the needed data scope; prefer a minimal locally redacted excerpt and retain
provenance. Never claim a redaction is exhaustive without evidence.

Retry/cancel, manual jobs, schedules, variables, releases and deployments are
mutations and may affect production. Do not enable hidden tools or fall back to
CLI/API commands to perform them under this preset. Stop for specific approval.
A failed/unavailable CI tool is a gap, not a reason to run fetched project code.
