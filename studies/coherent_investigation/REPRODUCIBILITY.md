# Reproducing the review

The pre-evaluation freeze is commit `5eec903`. The protocol, investigator/checker code, ten new packets, answer keys, public anchors and source/check signature bundles were frozen before the first held-out request. Later reporting utilities do not change the experimental methods.

Run from the repository root with Python and the project's cryptography dependency installed:

```sh
python -m coherent_investigation.verify_export
```

This verifies the committed artifact mirror, frozen source hashes, source/check signatures and bindings without credentials, private signing keys or API calls. The manifest maps the original ignored results paths to committed artifacts. Public anchors establish consistency with the archived study key; in a deployment the trusted recorder key must be pinned independently, not accepted from the target.

Inspect `OUTCOMES.md` and the complete final responses in `assessments/`; scoring criteria and caveats are in `PROTOCOL.md`. The answer keys in `artifacts/operator/heldout/` are operator-only evaluation records. They are now archived for reproducibility but were never sent to experimental models. `development_assessments/` and `development_failures/` preserve successes, truncations and blocked-before-dispatch slots. The artifact mirror preserves earlier development code and prompt variants.

The raw API request/response and stream journals, including internal model reasoning, remain in the local ignored `results/coherent_investigation/api/` directory. Published-within-this-repository assessment artifacts contain final answers only. No private signing keys or credentials are exported. Provider request identities and actual costs are in `COSTS.json`.

Local deterministic checks for the study implementation are in `coherent_investigation/test_local.py`. They cover fixture consequences, cryptographic rejection, permission-independent checks, equal fact access, reference validation, budget guards and stream recovery. Tests are unblinded automated implementation validation, not independent human validation.

Do not run `coherent_investigation.run` to inspect results: that command is a paid-dispatch entry point. The completed local ledger and terminal slot files prevent duplicate requests; a fresh checkout does not contain that private runtime ledger. A new study needs a separately authorized budget, new durable ledger and clearly labeled protocol. Do not modify the archived held-out examples or use their outcomes to claim a fresh held-out evaluation.
