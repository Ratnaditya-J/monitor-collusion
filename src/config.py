"""Central config for the monitor-collusion feasibility pre-check.

Nothing here has been run yet. The pre-check exists to decide, cheaply, whether
the activation arm is viable on a probeable open model before any larger build.
See docs/PREREGISTRATION.md section 8 for the gate.
"""

# Target model to probe (open, dense so the residual stream is clean to probe).
# Start small for a first local signal; scale up if the signal is borderline.
# Run-2 (Option 2): larger, different-family probeable model + subtler violations.
TARGET_MODEL = "Qwen/Qwen2.5-32B-Instruct"                 # larger, different family
OTHER_MODEL = "NousResearch/Meta-Llama-3.1-8B-Instruct"    # other-author for self-recognition + 8B comparison

# Probe at a spread of layers; report per-layer so we see where signal lives.
# Fractions of total depth, resolved at runtime.
LAYER_FRACTIONS = [0.25, 0.5, 0.75, 0.9]

# Probe battery (gate0c settings that were robust cross-distribution).
LOGREG_C = 0.05
N_BOOTSTRAP = 1000
SEED = 0

# Dataset sizes for the pre-check (small by design; this is a gate, not the study).
N_PER_CLASS = 200          # per framing for the monitoring-awareness probe
N_SELFREC_PER_CLASS = 60   # per generator for the self-recognition probe (bounded run)

# Gate thresholds (see PREREGISTRATION.md sec 8). A probe "clears" if its mean
# AUROC CI lower bound beats both chance and the surface (TF-IDF) baseline.
GATE_MIN_AUROC_OVER_CHANCE = 0.60   # lower CI bound must exceed this
PRECISION = "bf16"                  # 32B does not fit fp32 on one GPU; bf16 is fine for a feasibility signal

OUT_DIR = "results"
