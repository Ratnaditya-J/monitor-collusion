# Investigator findings: presentation sources

[Download the PowerPoint presentation](agent-investigator-findings.pptx)

The presentation compares investigator models and evidence setups. Numbers below are assessment counts from selected tests, not general model failure rates. The earlier live-generated collusion messages are a separate experiment from the four published benchmark attack families.

| Deck topic | Report and evidence | Implementation |
| --- | --- | --- |
| Astra and Qwen comparison / Run 1 | [Results](../studies/qwen_comparison/RESULTS.md), [all outcomes](../studies/qwen_comparison/OUTCOMES.md), [operational failures](../studies/qwen_comparison/OPERATIONS.md) | [Qwen test runner](../source_fidelity/qwen.py) |
| Run 2: added recorder observations | [Results and limitations](../studies/recorder_observations/RESULTS.md), [all outcomes](../studies/recorder_observations/OUTCOMES.md) | [Collector and workflow](../recorder_observations/README.md) |
| Run 3: coherent evidence | [Results](../studies/coherent_investigation/RESULTS.md), [protocol](../studies/coherent_investigation/PROTOCOL.md), [reproducibility](../studies/coherent_investigation/REPRODUCIBILITY.md) | [Investigation workflow](../coherent_investigation/README.md) |
| Cryptographic signing | [Signed-evidence comparison](../studies/spineframe_qwen/RESULTS.md) | [Evidence kernel](../evidence_kernel/README.md), [upstream attribution](../evidence_kernel/vendor/spineframe/ORIGIN.json) |
| Agent quotations | [Exact excerpts](../studies/auditor_manipulation/TARGET_SNIPPETS.md), [complete selected actions and receipts](../studies/auditor_manipulation/EVIDENCE_TARGET_SNIPPETS.json) | [Adaptive protocol](../studies/auditor_manipulation/ADAPTIVE_V7_PROTOCOL.md) |
| What the collusion attempts established | [Results with correction](../studies/auditor_manipulation/ADAPTIVE_V7_RESULTS.md), [offline validity review](../studies/auditor_manipulation/GO_NO_GO_REVIEW.md) | [Study guide](../studies/auditor_manipulation/README.md) |

## Interpretation

- Run 1 and Run 3 changed cases, permission clarity and investigation interfaces as well as evidence. The cross-version comparison does not isolate an evidence-only causal effect.
- Run 2 improved exposure recognition in some assessments, but those reports still did not classify the activity as unauthorized.
- Signing protects integrity relative to trusted keys. It does not guarantee complete recording, truthful upstream observations or correct reasoning.
- Target quotes are exact outputs of explicitly instructed adversarial simulations. Coordinated stories did not establish successful deception; both second-round investigators retained the unauthorized-write finding.
- Reports retain operational failures and scoring limitations. Automated model reviews are not independent human validation.

Curated reports and exported evidence are included. Some historical raw-response archives are tracked; other raw archives, private signing keys and credentials remain local. Old reports may retain local archival paths. Use this index and the exported study evidence for shareable references.
