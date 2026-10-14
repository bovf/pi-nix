# Reviewed OpenAI subscription context limits

`pi-coding-agent.openaiCodexContextWindows` exports the reviewed map in
[`openai-codex-context.json`](../overlays/pi-coding-agent/openai-codex-context.json).
It is packaging metadata, not a changed core catalog or custom provider.
`badwater-ai` consumes it only when `badwater.ai.pi.openai.maxContext = true`.

Audit: 2026-10-13, rechecked with Pi 1.2.0 during the 2026-10-14 full update.
The packaged and current public
[OpenAI-Codex catalog](https://pi.dev/api/models/providers/openai-codex?types=chat)
list nine chat IDs. Eight official model specification cards explicitly declare
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

The same reviewed chat IDs are overridden under current `openai` and legacy
`openai-codex`, without replacing model lists, OAuth, APIs, URLs, price tiers,
output limits, image capabilities or classifier models. The switch does not
choose an authentication method, grant server access or increase plan quotas.
A local 1.05M declaration is not proof that an account accepts a 1M request.
Larger prompts can consume more allowance and increase latency.

## Regression

```sh
nix build .#checks.x86_64-linux.openai-context --no-link
```

The Nix sandbox uses private HOME/cwd, `PI_OFFLINE=1`, the actual packaged Pi
runtime, and native subagent preload/factory. It checks all nine IDs on both
routes, unchanged other metadata (including classifiers), per-model compaction,
native SDK selection and 18 inert child startup/shutdown cycles. No prompt,
credential, real media or provider call is used. Review/update the map and its
sources whenever the packaged subscription catalog changes; unknown future IDs
are not guessed. Non-native platforms are evaluation-only on a Linux host.
