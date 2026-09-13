# Completed study handoff

Status: complete; no remaining paid requests or unresolved billing. Dispatch is closed by `results/spineframe_qwen/api/STOP.json`. Do not remove it, delete failed slots, reuse request IDs with changed payloads or sample replacements.

Branch: `aditya/spineframe-qwen-evidence`. Integration/freeze commit: `662bac1`. SpineFrame source commit: `4b0dc0780933ec3083cb8eb5356d3b024231d563`. Prior Qwen comparison and Astra findings remain unchanged. No push or external publication was performed.

Read RESULTS.md, OUTCOMES.md, PROTOCOL.md and OPERATIONS.md in this directory. Every completed final assessment is reproduced under assessments/. COSTS.json contains all 80 new generation-history reconciliations. Full raw records and frozen public evidence remain locally under results/spineframe_qwen; private keys are ignored by Git.

Outcome: unsigned 0 full / 3 partial / 7 misses on 10 completed attacks; signed 0 full / 4 partial / 4 misses on 8. Nine unsigned and ten signed completed benign assessments have no unsupported focal accusation. Signed delivery repeats are both operational failures, so no completed delivery comparison is available. The additional unsigned benign failure is an empty final assessment.

New cost $0.19689960; cumulative Qwen allowance spending $0.29592635; remaining $0.70407365; holds $0. A remaining balance does not authorize an unplanned new experiment.

Reproduce local verification using a Python with cryptography installed:

```sh
python -m unittest tests.test_evidence_kernel tests.test_evidence_transport -v
python -m evidence_kernel.validate_completed
python -m evidence_kernel.report
```

The latter two commands use this completed study's local results. The kernel and fixtures do not need the external SpineFrame checkout. The investigation sandbox currently requires macOS sandbox-exec, as in the original comparison. `python -m evidence_kernel.reconcile` makes read-only provider-history queries and never generates an assessment. Do not run preparation over the existing freeze.

Next scientific hypothesis, not yet run: safe consequence-checking tools may help an investigator trace a file or value to its actual destination. Test against equal-fact unsigned controls and benign counterparts. Keep broad investigation instructions. Separately, measure cryptographic-record benefits under actual evidence tampering; this completed batch did not manipulate record integrity. Do not call this study independent historical action witnessing or a reliable general detector.
