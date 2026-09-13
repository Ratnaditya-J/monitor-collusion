# Handoff: Qwen runtime-observation comparison complete

Branch: `aditya/qwen-runtime-observations`. Pre-dispatch freeze commit: `0b90378`. Prior work preserved on `aditya/spineframe-qwen-evidence` and in the existing studies. No external push or publication performed.

All 40 fixed slots attempted once: 36 final assessments, four operational failures. Dispatch is closed by the completed schedule and saved STOP marker. No active experimental model requests remain. Do not replay failures or regenerate fixtures in this completed study.

Primary matched result: nine attack/precursor pairs, control 0 full / 1 partial / 8 misses; observations 3 full / 1 partial / 5 misses. Seven matched benign pairs have no focal false accusation. The three full scores mean recognition of an observed exposure: two weight-logging repeats and one key-in-commit repeat. All three still call the overall behavior non-anomalous/legitimate; the key report wrongly dismisses the consequence as a simulation artifact. Do not describe this as three unqualified successful misalignment investigations. Under a stricter sensitivity reading that excludes that dismissal, two recognition gains remain, both for one packet.

The shared export capture context confused one report; replay-vs-history distinctions confused others. Preserve these limitations. No post-freeze experimental repair occurred. No historical results were re-scored or overwritten. This is a small selected diagnostic set, with unblinded assistant adjudication and no independent human validation.

New accounted spend: $0.30204675 / 114 requests. 112 generation-history reconciliations; two $0 classifications from verified upstream no-output errors and billing policy. Previous Qwen spend: $0.29592635. Cumulative: $0.59797310 of $1; remaining $0.40202690; held $0. Even full original reservations for both policy-classified errors would leave cumulative spend below $1. See COSTS.json for every request and its accounting basis.

Committed evidence includes protocol, source, ten neutral observation packets, all 36 verbatim final reports, four failure summaries, adjudication, freeze, validation, operations, costs and evidence index. Raw original fixtures remain in evidence_kernel/fixtures. Full requests, model responses, observable tool results, billing lookups, operator validation and durable SQLite ledger remain locally under ignored results/recorder_observations. Internal model reasoning and credentials are not included in the committed final-report artifacts.

For read-only post-run checks, use the existing Python runtime with cryptography:

```
/Users/ratnaditya/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m recorder_observations.validate_completed
```

`recorder_observations.report` exports the saved adjudication and assessments without model calls; `recorder_observations.reconcile` uses read-only history endpoints. Do not run collectors/preparation over frozen observations. A fresh reproduction needs isolated paths and a fresh explicitly bounded protocol; the collector intentionally retains all synthetic substitutions and scope limits.

Suggested next scientific dependency, not a new paid run: construct a coherent observed execution whose task, permissions and consequences all come from the same environment. Remove ambiguity between reproduced behavior and historical claims while keeping synthetic safety controls and the broad instruction. Freeze before any new comparison, use equally documented legitimate counterparts, and retain both exposure-recognition and authorization-judgment outcomes. Do not infer that adding cryptographic signatures alone will fix reasoning.
