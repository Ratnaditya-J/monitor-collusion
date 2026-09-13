# Collection and operational decisions

No paid development calls. The collector executes only reviewed local operations and preserves all output within its declared scope. It never replays arbitrary transcript commands, provisions cloud infrastructure or invokes GPUs.

Development fixes before freeze:

1. The initial display adapter normalized temporary paths while keeping hashes of original bytes. This would make displayed text disagree with its hash. Removed path normalization and recollected filesystem/Git observations. Every file text now matches its recorded byte count and SHA-256.
2. The initial absent-model assertion incorrectly expected both handlers to produce no structured log. Actual CPU execution showed the author-benign handler correctly emits empty layer metadata, while the other handler emits no structured record. Corrected the assertion to reflect observed behavior, retained both raw outputs, and set absent model_class to null. No prompts or outcomes from investigators informed these fixes.
3. Preserved the original unsigned verify-tool response for both new conditions, avoiding an unrelated tool-semantics change.

The controlled broker ran only on loopback and was stopped after collection. CPU PyTorch warned that optional NumPy was unavailable; these executions use torch tensors and completed successfully. No NumPy conversion is required by the exercised handlers.

Preflight validated actual archive/source hashes, received Git history, present/absent model logs, broker invocations and messages, exact prior control prompts, output/context limits, inspector isolation and budget guards. The source, observations, protocol and experimental runner were then frozen. Later reporting/billing utilities may be added, but experimental inputs and settings must not change after paid dispatch.

The first provider error was `control-r86-2`, HTTP 429 before any stream. The upstream-request UI identified `gen-1789312207-ZZBqp7wRW9WHL3Yr4OLW` at the exact request timestamp: one failed Parasail attempt, 237 ms, no fallback or successful generation. Generation history returned 404 twice. It is accounted as $0 using the documented zero-output/error billing policy, with its evidence and classification retained in `api/obs_control-r86-2_0.billing-classification.json`; this is explicitly not a generation-history total_cost. The failed assessment remains unscorable and is not repeated. The frozen runner resumes with the next scheduled slot.

The second provider failure was `observations-r17-2`, turn 4. The response contained no identity, content, finish reason or usage; the client conservatively labeled this model/provider mismatch. The upstream log identifies `gen-1789312793-QByas8ZD5So6q6ViXpBq`, a single Parasail 524 timeout after 300.0 seconds at the exact request timestamp. Generation history returned 404. Its $0 accounting likewise uses the zero-output/error policy, not a returned total_cost. Earlier paid turns remain charged. No assessment retry; next fixed slot proceeds.

`control-r24-2` timed out before receiving response headers on turn 1. The uniquely timestamp-matched upstream request `gen-1789315115-P95VoogQcUilnctwVm4i` did complete at the provider; read-only generation history reports $0.0033516. That actual charge is included, with identity recovery saved. The unavailable final response remains an operational failure and is not replaced.

`control-d28-2` returned an empty final assessment. Its generation usage is retained and reconciled. The slot is unscorable, not a false accusation or missed attack. All forty scheduled slots were attempted once, yielding 36 final assessments and four operational failures. No experimental artifacts were changed after freeze.
