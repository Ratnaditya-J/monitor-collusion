# Coherent investigation study

Three conditions share the same current local execution and trusted owner permission records: ordinary Qwen, Qwen plus deterministic evidence checks, and the latter plus a deterministic index, explicit permission-comparison and reference-gate workflow. Every condition receives equivalent host verification through the vendored SpineFrame primitives. No API key, signing key, operator answer or another case is supplied to an investigator.

The collector performs local archive, Git, file and SQLite actions with safe synthetic data. Sources and derived checks are signed separately, with input and implementation hashes binding the derivation. The target-role actions are scripted; this is not a live-target or search-agent evaluation. There are no enforcement hooks.

The complete setup and scoring contract are in [the protocol](../studies/coherent_investigation/PROTOCOL.md). Existing case themes are development material; held-out cases vary surfaces within those themes. Local checks are in `test_local.py`. Output budgets and condition input costs are explicit in the cost plan.

Run from the repository root with a Python environment containing cryptography. Development and freeze commands are intentionally separate:

```
python -m unittest coherent_investigation.test_local -v
python -m coherent_investigation.prepare develop
python -m coherent_investigation.prepare freeze
python -m coherent_investigation.run
```

Do not regenerate an existing frozen study. `collect` refuses to overwrite executions. `run` skips terminal slots; the transport refuses changed/unknown request IDs and enforces the cumulative Qwen allowance. A request with uncertain billing halts paid dispatch for read-only reconciliation; a failed assessment is not replaced. A new study needs a separate data root, protocol and explicit budget.

Raw responses may include internal reasoning and remain under ignored results/coherent_investigation. Reports export only final assessments and the requested observable permission comparisons. Private signing keys remain under ignored operator directories.
