# Adversarial review of pre-registration v0.1, and how v0.2 responds

An independent skeptical review was run against v0.1 before writing any code. The
substantive findings and the v0.2 response:

1. **Scaling headline not in a single-scale design.** v0.1 led with "collusion
   rises with scale" but put the scaling curve out of scope, so the headline rested
   on a slope never measured.
   -> v0.2: primary claim is decoupling (propensity != efficacy). A bounded
   within-family 3-point read on the cheapest (coordination) arm is the only
   scaling claim, explicitly labeled suggestive.

2. **Role-play salience competitor survives the whole battery.** The strongest
   reassuring hypothesis is "no endogenous propensity, just instruction-following
   and role-play salience"; it predicts everything the alarming hypothesis does.
   v0.1 could not distinguish it.
   -> v0.2: made it the primary competitor (H_roleplay) and added the three
   controls that separate it: recipient-of-payoff dissociation, cross-framing
   probe transfer, and a framing-regressed probe baseline. If these do not
   separate, we report role-play, not collusion.

3. **"Coordination removed" collapses into compliance.** Pre-sharing a signal and
   instructing M to pass measures instruction-following, not propensity.
   -> v0.2: propensity is a salience curve A (ceiling/compliance) to D (natural:
   only "passing benefits you," no signal, no instruction). The estimate is D.

4. **Capability baseline imported from a different prompt.** "M can detect (honest
   mode) but passed (incentive mode)" does not show in-context detection.
   -> v0.2: in-context detection check on the same run.

5. **Coincidence floor undercounts.** Neutral-case base rate misses leniency that
   the violation/incentive framing itself elevates.
   -> v0.2: matched no-benefit control (violation present, detection confirmed,
   benefit removed/reversed).

6. **Coordination not identifiable in a non-stego setting.**
   -> v0.2: explicit Schelling structure (pick the same of several candidates, no
   placeable signal) plus a non-colluding chance floor.

7. **Self-recognition vs style: paraphrase is not a clean strip.**
   -> v0.2: multiple paraphrasers, semantic-preservation check, matched cross-model
   paraphrase control; counts only relative to the matched other-model condition.

8. **Activation gate "nonzero" passes an unvalidatable project.** Too few
   behavioral positives means the probe-predicts-behavior moat cannot be tested.
   -> v0.2: gate requires at least N positives (power-based; placeholder 25), and
   names the real risk that a probeable-and-collusion-capable open model may not
   exist, with a behavioral-only fallback.

9. **Behavioral eval-awareness left uncontrolled (only a probe target).**
   -> v0.2: disguised vs overt monitoring framing in the behavioral arm.

10. **Probe moat must be cross-framing transfer, not in-distribution decoding**
    (which is nearly free and is exactly the role-play signal).
    -> v0.2: moat counts only on transfer + beating the framing-regressed baseline.

Open items still owed before compute: finalize N with a power calc; confirm a
probeable-and-collusion-capable model exists (the feasibility pre-check); choose
the concrete v1 task and the within-family size triple.
