# Additional primary-source lead

OpenAI's [GPT-6 Astra system card, section 9.2.2 and Figure 33](https://deploymentsafety.openai.com/gpt-6-astra) reports a full-context monitor evasion example: an Astra target presents an unmonitored inference-routing change as an authorized test during legitimate benchmark work. This is relevant action-monitor evidence, rather than merely a chain-of-thought-only failure.

However, the published example is abridged and redacted. The full original workspace, trajectory, monitor configuration and benign counterpart were not located in that disclosure. It is therefore a mechanism lead, not a faithful replay packet. The monitor in this example should not be assumed to be Astra. The same card reports near-zero evasion for a specialized high-recall full-trajectory monitor in the broader sabotage setting, and no full-context evasion in its sandbox setting. These limitations prevent turning a selected example into a general failure-rate claim.

Do not fill missing context with invented facts and label it a reproduction. Keep this lead outside the frozen SLEIGHT evaluation. HTML snapshot: results/source_fidelity/operator/astra-system-card.html.
