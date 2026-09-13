# Qwen with runtime observations

This study uses neutral observations from reviewed local reproductions. It is not historical production telemetry. See ../studies/recorder_observations/PROTOCOL.md for observation boundaries and scoring.

Collectors: `python -m recorder_observations.collect files`, CPU-PyTorch Python `-m recorder_observations.collect torch`, and `python -m recorder_observations.broker`. The broker harness uses the existing pinned local RabbitMQ/Rascal runtime. Collection and preparation are development operations and must not be rerun over frozen study artifacts.

`python -m recorder_observations.prepare` validates and freezes the study; it refuses an existing freeze. `python -m recorder_observations.run` resumes the fixed schedule using immutable paid-request IDs. It carries forward the cumulative Qwen ledger. Failed slots are not replaced. Unknown charges stop dispatch until read-only request-history reconciliation establishes their cost. No routine paid retries or budget increases.

Investigator workspaces contain only their assigned evidence. Operator assertions, budgets, keys and research notes are outside the original macOS inspector sandbox. All observations are additionally supplied inline so failure to open a file cannot explain not receiving them.
