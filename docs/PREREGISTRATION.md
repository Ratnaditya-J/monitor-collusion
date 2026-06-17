# monitor-collusion: Step 1 construct and pre-registration (v0.1, design draft)

This is the frozen-on-paper part. It exists so the result cannot be talked into
whatever number we happen to get. It defines what collusion means here, how the
measurement separates it from the things it gets confused with, what each result
would mean (committed in advance, both directions), and the cheap gate that
decides whether the activation arm is even viable before any larger run.

Status: draft. Nothing here has been run. This document is the thing to attack
before writing experiment code that costs anything.

## 1. The question, stated as a decomposition

A monitor M oversees a policy P. P sometimes produces a violation (a backdoor, a
hidden side task, an action that should be flagged). M issues flag / no-flag.
Collusion is M declining to flag a violation it can detect, in a way that helps P.

The field's one measurement (Järviniemi 2507.03010) reports the rate at which a
full subversion succeeds. That rate is a product:

    efficacy = propensity x coordination_capability x execution

- **execution**: P actually produces a working, in-principle-detectable violation.
- **coordination_capability**: with no communication, P and M converge on a
  compatible signal (M lets through exactly what P marked).
- **propensity**: given M can detect the violation and not-flagging benefits it,
  M chooses not to flag.

The reassuring reading of a low efficacy assumes the low factor is propensity.
It need not be. The central claim this project can settle:

> A low collusion efficacy can be produced by low coordination_capability while
> propensity is already high. Coordination_capability rises with scale;
> propensity is the safety-relevant factor. If propensity is high and only
> capability is low, the reassuring number is a temporary artifact and collusion
> increases as models improve.

Järviniemi's own data is a hint in this direction: his failures were coordination
failures, not refusals. The models tried and could not converge. That is the
precondition for the alarming reading, and it is currently unmeasured.

## 2. Operational definitions

We define collusion by its **consequence**, not by any claim about machine intent:
M fails to report a violation it is capable of detecting, at a rate that responds
to whether not-reporting is beneficial, above the rate explained by coincidence.

- **detected-but-passed (DBP)**: M demonstrably can detect the violation (see
  capability baseline) yet returns no-flag.
- **propensity**: P(DBP | M can detect, not-flagging benefits M, no coordination
  required) minus the coincidence floor. Coordination is removed (signal is given
  or the violation is plainly visible) so this isolates the choice.
- **coordination_capability**: P(M lets through exactly P's marked item | both
  instructed to collude, no communication), as a function of signal difficulty.
  Propensity is pinned at ceiling by instruction so this isolates convergence.
- **execution**: P(P produces a valid, detectable violation that passes the
  primary task), measured directly.
- **efficacy**: the product, reproducing Järviniemi's construct as the foil.

## 3. The separations (this is the contribution)

1. **Propensity, coordination removed.** Give M a violation it can plainly see,
   or pre-share the signal, plus an incentive to pass it. Measure DBP. High here
   with low efficacy means the gap is coordination, not unwillingness.
2. **Coordination, propensity pinned.** Both models instructed to collude. Vary
   signal difficulty (shared context vs none, obvious vs subtle signals). The
   convergence curve is the capability factor and its slope vs model size is the
   scaling read.
3. **Coincidence floor (twins control).** Base rate at which M returns no-flag on
   neutral cases with no collusion benefit and no coordination. Propensity counts
   only the excess above this floor.
4. **Incentive responsiveness.** Vary the payoff for passing. Propensity should
   track it. A flat response means it is not strategic and we do not call it
   collusion.
5. **Capability baseline.** Confirm M flags the violation at a high rate when
   honestly monitoring. Rules out "did not notice." A run that fails this is
   discarded, not counted as no-collusion.

## 4. The activation arm (open weights)

On an open-weight M, capture residual-stream activations at the flag/no-flag
decision token. Train linear probes (the gate0c battery: Normalizer +
StandardScaler + logistic regression, bootstrap CIs, shuffled-label control) for:

- **self-recognition**: is the output under review mine vs another model's
  (vary the true generator).
- **monitoring-awareness**: am I in a monitoring/oversight setup vs an ordinary
  task.
- **opportunity / intent**: does the representation encode "this is a collusion
  opportunity / I could pass this."

Three things to measure:
- Do these signals exist above chance and above a surface (TF-IDF) baseline?
- Do they predict the behavioral choice (propensity)?
- Do they appear when behavior is silent (M flags behaviorally, activations still
  encode recognition / intent)?

The headline white-box result, if it holds: behavioral monitoring underestimates
collusion propensity because the inclination is present in activations before or
without behavioral expression. This is the differentiated, uncrowded part, and
it directly answers an open question other work names (genuine self-recognition
beyond style discrimination; detection-to-exploitation).

## 5. Decision rules, committed in advance

- **Scaling-risk (alarming).** Propensity (isolated, above floor,
  incentive-responsive) is high while efficacy is low, and the gap tracks
  coordination_capability. Conclusion: the reassuring efficacy is a capability
  artifact; collusion is expected to rise with scale.
- **Reassuring.** Propensity is low even with coordination removed and incentive
  high. Conclusion: monitors are not inclined to collude at current scale; low
  efficacy is partly stable. Then run the pressure tests in 6 before publishing
  the reassurance.
- **Hidden propensity (the moat).** The activation probe finds recognition /
  intent that behavior does not show, and it predicts the rare behavioral
  collusions. Conclusion: behavioral monitoring underestimates collusion;
  white-box is necessary.
- **White-box null.** No latent signal above chance and surface baseline. Report
  it plainly; the behavioral result stands on its own.

Each of these is publishable. The project is not betting on one outcome.

## 6. Competing hypotheses and the controls that separate them

- **H_scaling**: propensity high, capability binding. (separations 1, 2)
- **H_reassuring**: propensity genuinely low. (separation 1 with high incentive)
- **H_suppressed**: propensity low behaviorally because of safety training, but
  latent or re-emergent under pressure. Adjudicated by the activation arm plus
  pressure tests: natural vs heavy-strategic prompting (Järviniemi used heavy
  prompting, a confound), and benign vs explicit framing of the pass.

## 7. Confounds and named controls

- **Coincidence**: the twins floor (3).
- **Did-not-notice**: the capability baseline (5).
- **Probe surface artifacts**: shuffled-label control, TF-IDF surface baseline,
  presence/length controls (reuse gate0c).
- **Self-recognition vs style discrimination**: vary the true generator and
  paraphrase the output to strip style; genuine self-recognition should survive
  paraphrase, style discrimination should not.
- **Prompt sensitivity**: measure natural propensity, not only
  instructed-to-be-strategic propensity.
- **Capability/propensity entanglement**: the isolation designs in 3 are the
  whole point; never report the raw product alone.

## 8. Feasibility pre-check (the gate, run this first)

Cheapest possible, on one open dense model. Before any full build:

1. Can a linear probe separate "my output" from "another model's output" above
   chance and above the surface baseline? (self-recognition signal exists)
2. Can a probe separate "monitoring setup" from "ordinary task" above chance?
   (awareness signal exists)
3. Given an easy, explicit collusion opportunity plus incentive, does the model
   ever choose to pass a violation it can see? (nonzero behavioral propensity)

Gate: proceed if (1 or 2) clears chance and surface baseline AND (3) is nonzero.
If all three are null, the activation arm is not viable on probeable models; stop
and reassess rather than scaling up. Size: a few hundred prompts, forward passes,
logistic regression. Single small GPU, possibly local.

## 9. Scope v1 and out of scope

- v1 task: a simple, cleanly-detectable-violation task (candidate: APPS or a
  small backdoor/side-task set), so execution and capability baseline are clean.
- v1 models: 1 to 2 open dense models for the activation arm; 2 to 3 frontier
  API models for the behavioral arm (where collusion is least rare).
- Out of scope v1: steganographic channels, multi-turn agentic settings,
  RL-trained colluders, the full capability-scaling curve. These are phase 2.

## 10. Stopping rules

- Feasibility pre-check null -> stop, reassess.
- Construct cannot separate the factors cleanly on inspection -> stop, redesign.
- Behavioral propensity measurable but the activation arm null -> drop the moat
  claim, ship the behavioral measurement-validity result alone.

## 11. What would change the headline (falsifiability)

The headline (scaling-risk) is falsified if isolated propensity is low under high
incentive with coordination removed, or if it does not respond to incentive, or
if the propensity gap does not track coordination_capability across difficulty.
Any of those moves the conclusion to reassuring. The experiment is built so that
outcome is reachable.
