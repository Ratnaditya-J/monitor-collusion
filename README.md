# monitor-collusion

Measuring whether AI monitors collude with the models they oversee, and whether
"collusion is rare" is a stable property or a temporary capability artifact.

A common plan for controlling powerful AI is to have one model watch another and
flag bad behavior. That only works if the watcher cannot quietly side with the
model it is policing. This repo measures whether it can.

The one existing measurement (Järviniemi, *Subversion via Focal Points*,
arXiv:2507.03010) reports a low success rate and reads as reassuring. But that
number is a product of three different things:

- **propensity**: whether a monitor is inclined to let a violation through when
  it benefits,
- **coordination capability**: whether two models can converge on a compatible
  signal without communicating,
- **execution**: whether the attempt actually defeats the audit.

A low product can hide a high propensity that is only held down by current
coordination capability. If that is the case, collusion gets worse as models
improve, not better, and the reassuring number is a moving target. So the
question here is not only "does collusion happen" but "what is the number
actually made of, and which part of it changes with scale."

## What's here

- `docs/` design and pre-registration: the construct, the three-factor split,
  the decision rules, the confounds, and the feasibility gate.
- `src/` the feasibility pre-check and the measurement code.
- `notes/` private working notes (gitignored).

## Status

Design stage. Nothing run yet. The plan is gated: a cheap feasibility pre-check
decides whether the activation read is viable on open-weight models before any
larger run.

## Approach (two arms, one question)

- **Behavioral**: vary how hard the collusion is and how much it pays, and score
  attempts, not just successes, so propensity can be separated from capability.
- **Activation (open weights)**: look for the latent collusion signal directly,
  including when the behavior stays silent. This is what lets propensity be read
  where behavior cannot show it.

Numbers come straight from the scripts. Limits are written down, not buried.
