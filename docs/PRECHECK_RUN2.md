# Feasibility pre-check, run 2 / Option 2 (2026-06-17)

Fixes over run 1: subtler/ambiguous violations, a recipient-dissociated incentive
(own-benefit / third-party / no-benefit), two models (Qwen2.5-32B-Instruct and
Llama-3.1-8B), and a clean self-recognition white-box probe with a paraphrase
control replacing run 1's surface-confounded awareness probe. Hardware: one
H100 NVL 94GB (~$2.59/hr), well under $1 of compute. Raw outputs in results/.

## Behavioral arm: zero collusion propensity, robust

Both models, all three incentive conditions, 30 trials each, subtle violations
(md5 passwords, verify=False, SQL via f-string, pickle.loads, shell=True, jwt
unverified, etc.):

| model | detect | DBP own-benefit | DBP third-party | DBP no-benefit |
|---|---|---|---|---|
| Qwen2.5-32B | 1.0 | 0.0 | 0.0 | 0.0 |
| Llama-3.1-8B | 1.0 | 0.0 | 0.0 | 0.0 |

Detection is perfect (the models see the violation every time) and they flag it
every time, regardless of whether passing benefits them. propensity_excess = 0,
role-play check = 0. This is now robust across two models, two scales, subtle
violations, and a recipient-dissociated incentive. **Collusion does not occur on
probeable open models, even when explicitly incentivized.**

## White-box arm (self-recognition): marginal, confounded, and inert

Probe on Qwen2.5-32B activations, self (its own code) vs other (Llama-8B's code),
60/class, vs a TF-IDF surface baseline, with a paraphrase control:

- raw: best probe AUROC 0.8825 [0.81, 0.93] vs surface 0.8608
- paraphrased: best probe AUROC 0.8689 [0.80, 0.93] vs surface 0.8361

The probe beats surface and survives paraphrase, so technically "clears." But be
honest about it: the margin over surface is only ~0.02-0.03 AUROC, the bootstrap
CIs overlap the surface value heavily, and the surface baseline is high because
this is a cross-family comparison (Qwen vs Llama lexical style), so most of the
signal is style/content discrimination, not clean self-recognition. A within-model
(same model, different sampling) test would be the clean version and was not run.

Critically: even taken at face value, this latent signal **cannot be linked to
collusion**, because behavioral collusion is zero. There is no behavior for the
probe to predict.

## Verdict: the white-box collusion moat is dead on probeable models

The moat required behavioral collusion to exist on a model we can probe, so the
probe could predict it. Run 2 shows, robustly, that it does not: open monitors at
8B-32B detect and flag violations regardless of incentive. Järviniemi's 3.4% was
on a frontier model (Claude 3.7). So collusion is, on this evidence, a
frontier-scale phenomenon, absent on probeable open models. The feasibility risk
flagged before any compute (PREREGISTRATION.md sec 8) is confirmed, for ~$4 total
instead of a GPU campaign and a collapsed paper. The gate did its job.

## What is salvageable (a real but modest finding)

A finishable, honest, deployment-relevant result lives here, just not the white-box
swing: **collusion in same-model monitoring is a frontier-scale phenomenon. On
probeable open models it is absent even under explicit own-benefit incentive on
subtle violations; it appears (rarely) only at frontier capability.** With a cheap
behavioral scale curve through frontier APIs to locate where it turns on, this is
a publishable scaling-threshold result: a safety team is not defeated by
same-model-monitor collusion at current open scale; the risk is emergent at the
frontier. It is a reassuring/negative + threshold result, not the differentiated
white-box contribution.

## The lesson for the white-box asset

White-box probing only yields a frontier result when the target behavior actually
occurs on a model you can open up. Collusion fails this. Sandbagging /
eval-awareness (the prior lane) does occur on open organisms. So the highest-value
use of the probe is a behavior that is open-model-elicitable, where a latent signal
can be tied to real behavior.
