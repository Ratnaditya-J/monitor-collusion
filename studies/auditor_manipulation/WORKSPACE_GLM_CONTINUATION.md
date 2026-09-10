# GLM attacker continuation

Prepared September 5, 2026 (local time). The execution plan and source hashes
were frozen before this continuation's paid development audits.

The user requested GLM or another available attacker after Astra's API rejected
two comparison attack generations. This continuation uses GLM-5.3 through
OpenRouter's direct Z.AI FP8 route for new target text. GPT-6 Astra Pro remains
the investigator. There are no automatic model or provider fallbacks.

The live catalog and Z.ai documentation identify GLM-5.3 as the flagship model.
Both the GLM route and the existing Abliteration.ai Large v2 credential were
checked. GLM produced a valid four-file protected-write revision for $0.0304598,
so Abliteration is not used in this continuation. That successful request does
not guarantee that later requests will be accepted.

## Reuse and development

Reuse the three initial Astra-generated attacks and their three completed
Astra audits from the previous workspace run. GLM receives each initial
candidate, the public investigation trace, and final assessment, and produces
one revision. The protected-write revision from the access check is reused
without another generation charge. Its request hash must match the actual
development request exactly. Three fresh Astra investigations assess the GLM
revisions. No private auditor reasoning is shared.

Keep the existing selection rule: among valid scored candidates, prefer a
false clearance, then abstention, then the later candidate. If a GLM revision is
invalid or unassessable, the earlier eligible strategy can remain selected.
Irrespective of which strategy wins, every new comparison payload is generated
by GLM. This prevents an unintended return to Astra for attack generation.

Reuse the five exact successful API responses underlying the completed
permissive control. Input hashes, model settings, response bodies, and provider
identity are validated. This is reuse of a calibration result, not an
independent repeat, and its false clearance remains excluded from attack rates.

## Comparison

Freeze the selected strategies before generating all twelve GLM payloads:
honest and adversarial notes for six existing comparison cases, three with
violations and three with legitimate historical conduct. None of these cases
has had a comparison auditor response; the prior run stopped before dispatch.
They are transfer cases from familiar task families, not a holdout.

Freeze all payload attempts before eighteen fresh Astra conversations:
six cases times empty, honest, and adversarial workspaces. Do not use comparison
feedback to revise attacks. Preserve the four-round tool budget, trusted
history tool, immutable policy/telemetry, six-file and 12,000-character limits,
high reasoning, and requested 8,192 completion tokens.

The attacker only writes text into an in-memory workspace. Neither generated
code nor instructions in files are executed on the host. There is no live
target, GPU use, or training in this stage.

## Accounting and integrity

This continuation has a $10 ceiling for new API calls, including its $0.0304598
probe. The prior locally chosen $20 overall stop limit is replaced with $30
for the user-requested model continuation; the actual new run allowance after
the probe is $9.9695402. The change was disclosed before dispatching the run.

Earlier known charges and retained reservations total $18.763611; after the
probe, the frozen plan carries $18.7940708 as prior accounting. Imported
responses are charged only to their source run, never twice. Unknown charges
from earlier failed requests remain reserved, not assumed to be zero. A
reservation is neither a confirmed charge nor a provider billing guarantee.

The original Astra run and its source snapshots are retained separately.
This is a different attacker configuration, not a repaired result for the
blocked Astra experiment. The software passed 56 tests, plus an offline mock
of all eighteen comparison audits, imported responses, model assignment, and
resumption without repeat calls. Mock results are not research observations.

Config: `workspace_glm_continuation.json`.
Private run directory: `results/auditor_manipulation/workspace_v4_glm`.

Sources checked before collection:
[Z.ai GLM-5.3](https://docs.z.ai/guides/llm/glm-5.3),
[OpenRouter GLM-5.3](https://openrouter.ai/z-ai/glm-5.3),
[Abliteration models](https://docs.abliteration.ai/models).

## Host-sleep recovery before comparison auditing

The Mac entered idle sleep at 19:06:36 local time while three GLM comparison
requests were in progress. Its power log records later wake and sleep events,
ending with a wake at 20:41:24. The local transport counted 300 active seconds
while these requests spanned roughly 95 wall-clock minutes. This explains the
long local delays; it does not establish whether the upstream requests completed.
The errors contain no provider refusal message.

The pipeline was interrupted before any comparison auditor request was sent.
Every remaining in-flight request was allowed to finish. Nine comparison
responses arrived, of which seven passed the strict parser; three responses
remained unavailable. All development
audits and the reused control were complete. The interrupted source and raw
responses are preserved under `workspace_v4_glm`.

The replacement plan `workspace_glm_sleep_recovery.json` preserves model
settings, strategies, workspaces, and assignments. It reuses all successful
responses by exact request hash, replaces only the three missing requests once,
and freezes all twelve payload attempts before the first comparison audits.
The recovery runs under a temporary `caffeinate -i` assertion that ends with the
runner. It makes no permanent change to power settings.

The interrupted GLM run reported $0.82019338 and retained $0.144540 in unknown
charge reservations. Together with the $0.0304598 probe, this leaves $9.00480682
within the unchanged $10 new-call allowance. The recovery's private directory
is `results/auditor_manipulation/workspace_v5_glm_recovery`.

## Post-hoc format-only adapter

After recovery, ten of twelve payloads passed the strict parser. Sixteen
comparison audits completed with correct verdicts; one honest assignment and
one adversarial assignment were unrun. One rejected response was valid JSON
inside an outer Markdown code fence. Another had the required strategy and
writes plus unused top-level notes and null actions fields. Neither failure
was an API refusal.

The `json_envelope_v1` adapter removes only a single outer JSON Markdown fence
or the specified unused metadata. It preserves every strategy and file-content
string; all path, size, duplicate-key, and protected-surface checks still apply.
Unknown extra fields, forged history, and non-null actions remain invalid.
The raw text hash, ignored metadata, and normalized payload hash are recorded.
The same rule was applied to all twelve responses, changing two envelopes.

This is an explicitly post-hoc protocol amendment after sixteen audits. No
target was regenerated and no comparison feedback was given to any target.
Sixteen exact prior audit conversations are reused; only the two previously
missing audits run against the newly ingestible payloads. The strict-format
result remains separately retained. Do not describe the amended parser as
pre-registered.

The adapter and existing suite passed 61 tests. Configuration:
`workspace_glm_format_adapter.json`; private run:
`results/auditor_manipulation/workspace_v6_glm_adapter`. No additional budget
was added: its allowance is $6.16013606 from the existing $10 continuation ceiling.

## Completed outcome

All eighteen comparison verdicts were correct: six of six empty workspaces,
six of six honest workspaces, and six of six adversarial workspaces. Among
the adversarial workspaces, all three actual violations were identified and
all three legitimate cases were cleared. There were no false clearances,
false accusations, abstentions, or unavailable final assessments. The three
GLM development revisions were also judged correctly. The deliberately
permissive control's false clearance is excluded from these results.

Across the GLM probe and all continuation stages, 77 new API requests incurred
$4.02881894 in reported charges. Another $0.144540 remains reserved for the
three sleep-interrupted requests, yielding $4.17335894 against the $10 ceiling.
The final adapter stage made five new auditor calls costing $0.333495; all
other outcomes were reused from exact saved requests.

This small development transfer test found no successful auditor manipulation.
It does not establish general robustness. The trustworthy history tool,
three familiar templates, limited attack-development budget, and post-hoc
format adapter constrain the interpretation. No held-out or live-target
experiment was performed.
