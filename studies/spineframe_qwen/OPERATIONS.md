# Operations and provenance

The original 40-slot protocol, model settings, fixtures, trust anchors and experimental code were frozen before paid dispatch. No outcome was fed back into the experiment. `evidence_kernel/reconcile.py` was added after dispatch solely to query billing history and settle existing request IDs; it cannot generate assessments.

The first operational failure was `verified-r71-1`: the eighth response lacked usage cost. The client retained a conservative reservation and stopped the batch. Read-only generation history for `gen-1789308974-dTfVuB8TAYtgp5wuuhJI` reported $0.00423235, within its $0.03584145 reservation. That charge was settled and the unchanged runner resumed at the next frozen slot. The failed slot was not retried or replaced and remains operationally unscorable under the frozen rule.

Source: SpineFrame commit `4b0dc0780933ec3083cb8eb5356d3b024231d563`; unchanged signing and event modules, extracted content-root function, Apache-2.0 license and origin manifest vendored locally. Original SLEIGHT fixture bytes are stored in `evidence_kernel/fixtures`, with source manifest and benchmark canaries intact. The external SpineFrame checkout is unnecessary at runtime.

This study signs historical imports; it does not retroactively witness the original actions. Host-owned signing keys and run/root anchors are inaccessible to the experimental inspector. The reusable host-mediated recorder is exercised with actual local file operations in deterministic tests, but was not present during historical benchmark generation.

A second failure, `verified-r71-2`, occurred on its first response. Both failed streams lack a finish reason and usage; the first has partial final text and the second none. Thus billing reconciliation does not turn them into completed assessments. Generation history for `gen-1789310169-xgcegmfbGzFNnK3Fprpq` settled the second charge; the full read-only reconciliation at this checkpoint covered 58 new requests totaling $0.14624640, with zero unresolved holds. The unchanged runner resumed after both failed slots, without replacement calls.

`structured-d28-1` returned an empty final assessment. The frozen runner marked it operationally unscorable and continued; the paid response was charged to the ledger. No replacement was dispatched.
