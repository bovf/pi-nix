# Reviewed OpenAI subscription context limits

`pi-coding-agent.openaiCodexContextWindows` exports the reviewed map in
[`openai-codex-context.json`](../overlays/pi-coding-agent/openai-codex-context.json).
It is packaging metadata, not a changed core catalog or custom provider.
`badwater-ai` consumes it only when `badwater.ai.pi.openai.maxContext = true`.

Limit-source audit: 2026-10-13; packaged-catalog compatibility rechecked with
Pi 1.5.0 on 2026-11-05. The nine-entry reviewed limit map remains unchanged.
Eight official model specification cards used for that review explicitly declare
1,050,000 context tokens and 128,000 maximum output tokens:

| Model | Maximum context | Official specification |
| --- | ---: | --- |
| GPT-5.5 | 1,050,000 | [GPT-5.5](https://developers.openai.com/api/docs/models/gpt-5.5) |
| GPT-5.6 Luna | 1,050,000 | [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna) |
| GPT-5.6 Sol | 1,050,000 | [GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol) |
| GPT-5.6 Terra | 1,050,000 | [GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra) |
| GPT-6 Astra | 1,050,000 | [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra) |
| GPT-6 Luna | 1,050,000 | [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna) |
| GPT-6 Sol | 1,050,000 | [GPT-6 Sol](https://developers.openai.com/api/docs/models/gpt-6-sol) |
| GPT-6.1 Sol | 1,050,000 | [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol) |
| GPT-5.3 Codex Spark (retired) | 128,000, unchanged catalog metadata | [Retirement](https://developers.openai.com/codex/models#deprecated-codex-models) |

Spark retired September 14, 2026; its continued presence in Pi's catalog is not
subscription availability. Its API model page returned 404 and announcement
fetch returned 403 during the audit, so 128k is retained catalog metadata, not a
newly verified active-model entitlement. GPT-5.5 is announced to retire from
Codex ChatGPT sign-in October 14, 2026. See [current Codex models](https://developers.openai.com/codex/models).
No override adds missing models or revives retired ones.

Pi 1.5.0's official release-pinned typed model catalog has SHA256
`f4dbabe79cda4b38aee4a761b23fd5eaf526ac2e28fed3c9ee86e37ca0e5d71e`
([immutable catalog](https://pi.dev/api/models/revisions/sha256-f4dbabe79cda4b38aee4a761b23fd5eaf526ac2e28fed3c9ee86e37ca0e5d71e?types=chat,image,classifier)).
Its `openai-codex` route now lists exactly eight chat IDs: the three GPT5.6
variants, GPT6 Astra/Luna/Sol and GPT6.1 Sol/Terra. Spark and GPT5.5 are absent on
that subscription route; both remain in the packaged `openai` API catalog.
The metadata keeps all nine reviewed entries, but overrides cannot add the two
absent subscription models. The selected GPT6.1 Sol remains present on both
routes. This is catalog presence, not an active-account entitlement claim.

GPT6.1 Terra is now in the stable release. Its packaged API route declares
272,000 context tokens and Codex declares 500,000. Both retain those release-owned
limits and ordinary compaction; Terra is deliberately outside the unchanged
nine-entry 1M override map. Its presence does not change the configured model,
account availability or backend entitlement. Never hydrate a different catalog
or inflate an unreviewed model merely to make a test pass.

The reviewed chat IDs are overridden where present under current `openai` and
legacy `openai-codex`, without replacing model lists, OAuth, APIs, URLs, price
tiers, output limits, image capabilities or classifier models. The switch does not
choose an authentication method, grant server access or increase plan quotas.
A local 1.05M declaration is not proof that an account accepts a 1M request.
Larger prompts can consume more allowance and increase latency.

## Regression

```sh
nix build .#checks.x86_64-linux.openai-context --no-link
```

The Nix sandbox uses private HOME/cwd, `PI_OFFLINE=1`, the actual packaged Pi
runtime, and native subagent preload/factory. It requires the exact eight-ID
subscription inventory, all nine reviewed API IDs and an explicit two-ID absent
subscription inventory. Unknown IDs/unexpected removals fail rather than being
silently skipped. It proves model overrides do not revive missing models and
checks unchanged other metadata (including classifiers), per-model compaction,
the unchanged selected GPT6.1 Sol, native SDK selection and exactly 18 inert
child startup/shutdown cycles (9 API + 7 subscription reviewed pairs plus 2
catalog-only Terra pairs with untouched context/compaction). No prompt,
credential, real media or provider call is used. Review/update the map and its
sources whenever the packaged subscription catalog changes; unknown future IDs
are not guessed. Non-native platforms are evaluation-only on a Linux host.
