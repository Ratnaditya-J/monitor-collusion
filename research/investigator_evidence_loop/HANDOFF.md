# Study handoff — completed

Branch: `aditya/investigator-evidence-loop`. Initial implementation/freeze checkpoint: `db10d42`. Do not change frozen code, fixtures, model settings, scoring or run order in place. No GPU, external publication or messages are authorized.

The pilot is complete: all 16 logical investigations and all blinded grading are finished. Neither condition was misled on the tested attacks; no benefit of the added procedure was demonstrated. See FINAL_REPORT.md. Do not dispatch further paid work under this completed study. Existing paid API credentials work directly with OpenAI Astra/Flex. No OpenRouter or RunPod access is needed.

## Reproduce or inspect without duplicate requests

1. Read `state.json`, `DECISIONS.md`, the frozen protocol and `FREEZE.json`.
2. Inspect `results/investigator_evidence_loop/api/ledger.json` and the SQLite ledger. A `reserved` request may still be active: inspect its process before any recovery. A `capped_unknown` request is stopped, its full maximum charge remains subtracted from available funds, and its actual bill is unresolved. Never release that reservation on assumption.
3. Run `python3 -m investigator_evidence_loop.study run` only if the study remains active and no prior runner is active. Settled logical IDs reuse saved responses. Checkpointed reports are in `results/investigator_evidence_loop/audits/`. The held-out order is fixed at 16 sessions. Do not alter prompts after viewing their outcomes.
4. The original whole-family grading command exceeds its packet envelope. The disclosed adapter is `python3 research/investigator_evidence_loop/complete_grading.py`; its completed request IDs use saved responses. Do not invoke a new grading plan. FINAL_REPORT.md documents why four blinded batches replaced two.
5. Verify the freeze, preserve all outcomes, write the final report and updated ledger/evidence index, commit locally, then mark the goal complete. Do not push.

## Resolved development defects

- Narrative write times initially disagreed with record metadata; fixed before held-out work.
- Signed origin records initially did not bind exact event timestamps. An ordinary development investigator correctly withheld judgment. The host now signs the complete activity digest; software checks it. The repaired legitimate and malicious development cases passed.
- A development request waited without an HTTP response. Its client was stopped. Its known maximum of $0.15375 remains held under `dev_d-308_defended_select`. The actual charge cannot be retrieved with this key (organization costs endpoint returned 403). Do not claim the cause is established as provider failure.
- The old socket timeout was insufficient as an elapsed deadline. Current code enforces 180 seconds for selection and 600 seconds for assessment/review, with at most one budget-checked transport recovery and no retries of returned assessments.

## Important interpretation limits

This is a compact, synthetic, two-stage audit with frozen researcher-authored adversarial explanations. It does not measure live collusion or open-ended navigation. Both conditions have exactly the same facts and tools. The two neutral control worlds are identical apart from case ID; do not treat them as distinct independent tasks. Blinded reviews are automated and use the same model family, not independent human validation. There is one paired observation per world, so no general reliability estimate follows.

The test suite contains 15 passing offline checks. The initial stopping suggestion was superseded by the user's direction to recover autonomously: bounded unknown charges stay reserved instead of unnecessarily blocking all safe work. Unbounded billing uncertainty still stops dispatch.

## Final state

- Metered known charges: $1.10435775; conservative completed-request charge accounting: $1.12097500.
- Keep $1.48490 reserved for two unresolved requests: $0.15375 for the development selection and $1.33115 for the original held-out r-864 ordinary assessment. Known metering plus the unresolved maximum is at most $2.58925775; the enforcement ledger is slightly more conservative.
- Conservatively uncommitted authorization: $27.39412500. This is not an invitation to spend the remainder.
- The original code/protocol/fixtures/scoring freeze still verifies. Grading batch splitting and an external watchdog are disclosed execution adjustments. Fifteen offline tests pass; all 16 reports are scorable, with no deterministic/semantic disagreements.
- Next useful external information would be authoritative billing for the two lost responses. Resolving that is not required to interpret the completed pilot. Do not release their reservations without evidence.
- Future research needs a distinct, costed question; this result does not justify more repetitions of the same two explanations.
