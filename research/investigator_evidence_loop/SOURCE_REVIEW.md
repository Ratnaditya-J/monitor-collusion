# Primary-source verification

Full texts were downloaded and read; paper claims below are not independent replications. Exact local source bytes and repository tree snapshots are indexed with SHA-256 in the evidence index.

## BenchShield

[Full text, arXiv 2609.11028v1](https://arxiv.org/html/2609.11028v1), particularly §§3–4 and limitations, distinguishes host-measured exposure, actual agent violations, and inconclusive coverage. Its trusted boundary includes the host recorder, lifecycle enforcement and claim machinery. A signed record authenticates a measurement; it does not establish arbitrary semantic adequacy. Its runtime/transcript comparison supplies different evidence, so its headline detection improvement does not establish the benefit of our same-information procedure. Multi-role privacy and action coverage are limitations. We adopt typed provenance, explicit coverage and inconclusive outcomes, not the paper's reported effect size.

The linked [BenchFlow repository](https://github.com/benchflow-ai/benchflow) was inspected at `b3b8afaf552719603f49df919cdc656b237bf5d3` (complete recursive tree and README). No path named BenchShield appeared; an exact corresponding released implementation was not located. BenchFlow's availability is not proof that the paper's complete system is reproducible. No downloaded code was executed.

## DriftNet

[Full text, arXiv 2609.10892v1](https://arxiv.org/html/2609.10892v1), especially evaluation and limitations, uses short synthetic AgentDrift trajectories and separates successful hijacks from resisted injections. The paper acknowledges generator/world regularities; task-disjoint evaluation does not establish generator-disjoint or real-agent transfer. Adaptive detector-aware attackers were not evaluated. We adopt separate positive/negative/insufficient controls, not its detector or reported accuracy as a prior for our investigators.

The linked [AgentDrift dataset](https://github.com/Asif-0209/AgentDrift) was inspected at `014a514fa998b4ac4519579fceb8a5884b379bda`. README/tree expose JSON trajectories, both split directories, task/world pools and leakage documentation. This verifies available data artifacts, not DriftNet weights or training reproducibility; those exact artifacts were not located in the inspected repository.

## Provider verification

[GPT-6 Astra model documentation](https://developers.openai.com/api/docs/models/gpt-6-astra) and [Flex processing guide](https://developers.openai.com/api/docs/guides/flex-processing) were read and saved. Authentication listed `gpt-6-astra`; a direct Responses request returned `READY`, `completed`, and `flex`. Standard pricing is $10/M input and $50/M output; cache-write pricing is $12.50/M input. Flex is documented at 50% of standard rates. The ledger reserves standard cache-write rates and releases only after returned metering is recorded. No OpenRouter credential, GPU or new credential was needed.

## Relation to earlier specification

The old GO_NO_GO_REVIEW and DECISIVE_TEST_SPEC remain intact. This version changes 30 conditional sessions with three repeats into 16 interleaved paired sessions with one repeat, adds genuinely insufficient worlds, and replaces human gates with explicitly labeled automated reviews under the user's new authorization. Frozen explanations are newly authored mechanism translations, not unchanged replay of old bundles. Defense is an investigator procedure using the same verifier, not privileged evidence injected only into its arm. The two-stage interface and explicit output ceilings reduce scope. These changes mean this is a new pilot, not execution or confirmation of the old preregistration.
