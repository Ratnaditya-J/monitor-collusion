# Feasibility model selection — 5 September 2026

The user requested the most capable available models, prioritizing recent
flagships. The selected target is GPT-6 Astra Pro. Auditors are GPT-6 Astra Pro
and Claude Fable 5.1. This compares one auditor from the target's family with one
from a different family; it does not isolate model-family effects or establish
which target model is the strongest attacker.

| Role/model | OpenRouter ID | Direct provider | Reasoning | Input/output price per million tokens |
| --- | --- | --- | --- | --- |
| Target and auditor: GPT-6 Astra Pro | `openai/gpt-6-astra-pro` | OpenAI | high, Pro mode through model ID | $10 / $50 |
| Auditor: Claude Fable 5.1 | `anthropic/claude-fable-5.1` | Anthropic | high | $10 / $50 |

The current run permits 8,192 output tokens including reasoning. Temperature is
omitted because the selected endpoints do not support it. Prompts require JSON,
but no repair model, JSON-repair plugin, or hidden additional generation is used.
The gateway excludes reasoning text from the returned content; usage and
whatever provider metadata is returned are preserved. No reasoning text is
passed to the other model.

OpenRouter advertises the endpoints as `gpt-6-astra-pro-20260903` and
`claude-fable-5.1-20260831`. We record those advertisements, the requested API
IDs, and the actual model/provider in every response. This is not a guarantee
that the provider's underlying weights cannot change. The runner disables
provider fallbacks and provides no alternate model. Responses that report a
different model must be investigated before interpreting results.

GPT-6 Astra is identified as OpenAI's most capable model in
[OpenAI's model documentation](https://developers.openai.com/api/docs/models/gpt-6-astra).
[OpenRouter's Pro listing](https://openrouter.ai/openai/gpt-6-astra-pro) describes
Pro as the same underlying model with Pro reasoning mode.
[Anthropic's Fable documentation](https://platform.claude.com/docs/en/models/fable-5-1/overview)
and [model overview](https://www.anthropic.com/claude/fable) establish Fable 5.1
as the current most capable generally available Anthropic model. Opus 5 was
considered, then replaced with Fable 5.1 before any calls were run.

## Costs and stopping

The run has 36 planned requests: 12 target generations and 24 audits. Prices were
verified against OpenRouter's model and endpoint APIs and copied into the run
configuration. Both selected direct routes cost $10/million input tokens and
$50/million output tokens, including reasoning; cache writes can cost more per
input token. The configured provider maximum-price filter prevents routing to
higher prompt/completion token rates.

As an illustration, 36 calls averaging 1,000 input and 2,000 total output tokens
would cost $3.96 before cache differences. Averaging 1,500 input and 4,000 output
tokens would cost $7.74. These are arithmetic scenarios, not measured forecasts.
The initial 32,768-token, maximum-effort calibration was costly: one target
attack used 27,323 output tokens and cost $1.49671. A preceding honest request
timed out without a response or reported charge; its $1.6790125 reservation was
retained. Two tiny compatibility checks cost $0.01742, and a high-effort honest
development calibration cost $0.07728. These are separate calibration records,
not outcomes from the final comparison. They leave $16.729578 of the $20 project
allowance for the six-case high-effort run after conservative reservations.

The project stop limit is $20 including calibration. Before a request, the
runner reserves its output allowance plus conservative byte-based input and
cache-write allowances. The Pro input allowance has a 16x multiplier because
Pro aggregates work and can bill repeated input tokens. Afterward, it uses the provider-reported charge if
available; otherwise it retains the reservation. It stops dispatching when the
next reservation would exceed the remaining budget. This is a client-side
control, not an account-level billing cap or control over spending by other
applications. Provider billing discrepancies remain a limitation.

No automatic retries or adaptive attack search are included. Any later retry,
model change, or attack-development phase must retain the original attempts and
be labeled separately. Six development cases do not support a general claim
about resistance to more capable or persistent attackers.
