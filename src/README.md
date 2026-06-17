# src: the feasibility pre-check

This is the gate from docs/PREREGISTRATION.md section 8. It decides, cheaply,
whether the activation arm is viable before any larger build. Nothing here has
been run yet.

## What runs

- `precheck_activation.py` (gate items 1-2): does the open model linearly encode
  "I am in a monitoring setup" (and optionally "this output is mine")? Probe
  battery: last-token residual, Normalizer + StandardScaler + LogisticRegression,
  stratified shuffled CV, bootstrap CIs, shuffled-label control, and a TF-IDF
  surface baseline the probe must beat.
- `precheck_behavioral.py` (gate item 3): at a near-natural own-benefit condition,
  does the monitor pass a violation it detects in-context, more than in a matched
  no-benefit control? Reports DBP excess.

## Run

    pip install -r src/requirements.txt   # torch installed separately
    python -m src.precheck_activation
    python -m src.precheck_behavioral

Outputs land in `results/` (gitignored). Edit `src/config.py` to change the model
or sizes. Defaults are tiny (Llama-3.2-1B) for a first local signal; if the signal
is borderline, rerun on a larger dense open model on a GPU.

## The gate decision

Proceed to the full build only if (activation item 1 or 2 clears chance and the
surface baseline) AND (behavioral item 3 yields enough detected-but-passed
positives to validate a probe, not merely nonzero). Otherwise fall back to the
behavioral-only decoupling result. The known risk this gate exists to surface:
a model that is both probeable (open, dense) and collusion-capable may not exist
in the small-open set. If so, we learn it here for a few dollars, not after a
GPU campaign.
