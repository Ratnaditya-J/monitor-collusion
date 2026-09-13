# Verifiable agent evidence

Self-contained SpineFrame primitives and a host-side adapter for monitor-collusion. Install Python dependencies with `pip install -r evidence_kernel/requirements.txt`. No sibling SpineFrame checkout or SpineFrame service is needed. The supplied investigator sandbox currently requires macOS sandbox-exec, as did the original study.

Vendored SpineFrame signing.py and events.py are unchanged. hashing.py extracts the unchanged compute_root_hash function. See vendor/spineframe/ORIGIN.json and LICENSE. We deliberately omit the workflow engine, enforcement, web UI and domain-specific claims heuristics. Ed25519 is the tested backend; optional post-quantum code is preserved upstream but is not required or claimed tested here.

`records.Recorder` wraps a host-executed operation, captures tool request/result or error and explicit actor/authorization metadata, and seals the record. Caller must own the recorder directory, signing key and trust registry outside target control. Actor labels authenticate the host's attribution, not arbitrary identities a target claims. The adapter does not automatically instrument every possible agent action or prevent side effects. A compromised recorder, stolen key, or unobserved side channel defeats these trust assumptions.

`records.verify` recomputes the ordered record chain, context and artifact commitments, then verifies SpineFrame's Ed25519 signature against a caller-pinned key and expected run ID. The experiment also checks a pinned root to reject stale signed snapshots. Never trust a public key merely because the evidence contains it. SpineFrame's standalone bundle signature check authenticates the declared root, so the adapter must also recompute the content root. Invalid integrity means untrusted evidence, not automatic proof of agent misconduct.

The fixed study imports old benchmark transcripts. Its signatures prove consistency since import, not that our recorder witnessed historical actions. U/V contain exactly the same semantic facts. No hidden answer key or consequence summary is added. See studies/spineframe_qwen/PROTOCOL.md.

Local tests: `python -m unittest tests.test_evidence_kernel tests.test_evidence_transport -v`. Preparation: `python -m evidence_kernel.prepare` (refuses an existing freeze). Running requires a frozen study and budget ledger: `python -m evidence_kernel.run`. Existing completed studies remain closed. Keys, API payloads and ledgers stay in gitignored results. Do not remove ledgers or failure records to force retries.
