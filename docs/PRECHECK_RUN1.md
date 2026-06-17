# Feasibility pre-check, run 1 (2026-06-17)

Model: NousResearch/Meta-Llama-3.1-8B-Instruct (fp32). Hardware: one L40S 48GB
(~$0.79/hr), a few minutes, well under $1. Raw outputs in results/ (gitignored).
This run is preliminary and crude by design; it is a gate, not the study.

## Results

**Activation arm, monitoring-awareness probe (gate item 2): UNINFORMATIVE.**
Probe AUROC 1.0 at every layer, shuffled-label control ~0.5 (so no CV leak). But
the TF-IDF **surface baseline is also 1.0**, so the probe does not beat surface
and the gate (which requires beating surface) correctly returns "does not clear."
Cause: the monitoring vs ordinary prompts differ in explicit framing words, so a
bag-of-words separates them trivially and the probe is just reading those words,
not a latent representation. This is a flaw in the test design (the adversarial
review of v0.1 predicted exactly this: "the probe decodes the prompt framing").
The monitoring-awareness probe must be redesigned surface-matched, or replaced by
the self-recognition probe with the paraphrase control (the cleaner white-box
target in PREREGISTRATION.md sec 4).

**Behavioral arm, DBP (gate item 3): ZERO propensity at this scale/elicitation.**
Detection rate 1.0 (the model always detects the obvious backdoor, so the
capability baseline holds). DBP 0.0 under the own-benefit incentive AND 0.0 under
the matched no-benefit control, over 20 trials each. The aligned 8B reliably
flagged the violation regardless of stated incentive.

Caveats on the zero: small n (rule of three: the true rate could be up to ~15%
and still show 0/20), greedy decoding, only 5 obvious violations, and a simple
stated incentive. So "zero" means "no collusion on obvious violations under crude
own-benefit framing," not "provably never."

## Gate verdict: does not pass

Two problems, one fixable, one fundamental:
- Fixable: the white-box probe test was surface-confounded; it tells us nothing
  yet about latent signal.
- Fundamental: zero behavioral positives means there is nothing for a probe to
  predict. The moat (probe predicts collusion) is unvalidatable on this model and
  elicitation, which is exactly the risk PREREGISTRATION.md sec 8 named (a model
  that is both probeable and collusion-capable may not exist in the open set).

## Honest interpretation

The feasibility risk flagged before any compute is showing up empirically: on a
probeable open 8B with clean (non-role-play) elicitation, behavioral collusion is
~0, so the white-box arm as specified cannot be validated. This does not yet prove
the project is dead, but it moves the burden onto: (a) a surface-matched /
self-recognition white-box test that beats surface, and (b) finding any condition
(subtler violations, stronger but still-non-role-play elicitation, or a larger /
less safety-tuned model) under which behavioral propensity is nonzero. If neither
materializes, the moat does not exist on probeable models and the project should
pivot.
