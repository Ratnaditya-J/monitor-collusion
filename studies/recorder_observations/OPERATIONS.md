# Collection and operational decisions

No paid development calls. The collector executes only reviewed local operations and preserves all output within its declared scope. It never replays arbitrary transcript commands, provisions cloud infrastructure or invokes GPUs.

Development fixes before freeze:

1. The initial display adapter normalized temporary paths while keeping hashes of original bytes. This would make displayed text disagree with its hash. Removed path normalization and recollected filesystem/Git observations. Every file text now matches its recorded byte count and SHA-256.
2. The initial absent-model assertion incorrectly expected both handlers to produce no structured log. Actual CPU execution showed the author-benign handler correctly emits empty layer metadata, while the other handler emits no structured record. Corrected the assertion to reflect observed behavior, retained both raw outputs, and set absent model_class to null. No prompts or outcomes from investigators informed these fixes.
3. Preserved the original unsigned verify-tool response for both new conditions, avoiding an unrelated tool-semantics change.

The controlled broker ran only on loopback and was stopped after collection. CPU PyTorch warned that optional NumPy was unavailable; these executions use torch tensors and completed successfully. No NumPy conversion is required by the exercised handlers.

Preflight validated actual archive/source hashes, received Git history, present/absent model logs, broker invocations and messages, exact prior control prompts, output/context limits, inspector isolation and budget guards. The source, observations, protocol and experimental runner were then frozen. Later reporting/billing utilities may be added, but experimental inputs and settings must not change after paid dispatch.
