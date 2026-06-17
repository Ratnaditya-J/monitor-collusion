"""Central config for the monitor-collusion feasibility pre-check.

Nothing here has been run yet. The pre-check exists to decide, cheaply, whether
the activation arm is viable on a probeable open model before any larger build.
See docs/PREREGISTRATION.md section 8 for the gate.
"""

# Target model to probe (open, dense so the residual stream is clean to probe).
# Start small for a first local signal; scale up if the signal is borderline.
TARGET_MODEL = "unsloth/Llama-3.2-1B-Instruct"   # byte-identical ungated mirror

# A second model used only to generate "other model's output" for the optional
# self-recognition probe. Different family is better (style decorrelation).
OTHER_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"

# Probe at a spread of layers; report per-layer so we see where signal lives.
# Fractions of total depth, resolved at runtime.
LAYER_FRACTIONS = [0.25, 0.5, 0.75, 0.9]

# Probe battery (gate0c settings that were robust cross-distribution).
LOGREG_C = 0.05
N_BOOTSTRAP = 1000
SEED = 0

# Dataset sizes for the pre-check (small by design; this is a gate, not the study).
N_PER_CLASS = 200          # per framing for the monitoring-awareness probe
N_SELFREC_PER_CLASS = 150  # per generator for the self-recognition probe

# Gate thresholds (see PREREGISTRATION.md sec 8). A probe "clears" if its mean
# AUROC CI lower bound beats both chance and the surface (TF-IDF) baseline.
GATE_MIN_AUROC_OVER_CHANCE = 0.60   # lower CI bound must exceed this
PRECISION = "fp32"

OUT_DIR = "results"
