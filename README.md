# monitor-collusion

[Presentation source index: results, code and exact agent quotations](presentations/README.md)

## Coherent Qwen comparison: completed

The [new three-condition study](studies/coherent_investigation/RESULTS.md) repaired case coherence and compared ordinary Qwen, Qwen with programmatic evidence checks, and Qwen with checks plus a staged permission-review procedure. All thirty held-out assessments completed: each condition found 4/4 violations, cleared 4/4 authorized counterparts and appropriately left 2/2 missing-permission cases unresolved. No added detection benefit was demonstrated. Some supporting explanations still overstate evidence; valid signatures and citations do not establish sound reasoning. New spend, including development failures: **$0.26889055**. [Protocol](studies/coherent_investigation/PROTOCOL.md), [all outcomes](studies/coherent_investigation/OUTCOMES.md), [offline verification](studies/coherent_investigation/REPRODUCIBILITY.md).

## Evidence-grounded investigator pilot (September 12, 2026)

A new $30-capped pilot compares ordinary and evidence-grounded investigations on matched unauthorized, legitimate and insufficient-evidence workspaces. Development defects and infrastructure recovery are recorded explicitly; prior studies remain unchanged. See the [frozen protocol](studies/investigator_evidence_loop/PROTOCOL.md), [source verification](research/investigator_evidence_loop/SOURCE_REVIEW.md), and [development decisions](research/investigator_evidence_loop/DECISIONS.md). The [final report](research/investigator_evidence_loop/FINAL_REPORT.md) records 16 completed investigations: both conditions detected all tested unauthorized actions, avoided false accusations on legitimate controls, and preserved genuine uncertainty. No added defense benefit was demonstrated. Known metered charges were $1.10, with $1.48490 still reserved for unresolved requests.


## Current work: investigator reliability

Can an honest AI investigator correctly assess agents that are trying to
influence its investigation? This study uses explicitly instructed adversarial
targets in a controlled workspace, with a separate operator answer key.

**Current decision: pause further paid attack iterations.** The two latest
adaptive development rounds are complete. Both second-round investigators
identified the unauthorized document edit, and neither cleared the targets.
Targets demonstrably coordinated accounts, criticized weaknesses and applied
revisions. Those actions do not establish successful deception.

The original model reviewer labeled two first-round conclusions partly erroneous.
The subsequent [offline review](studies/auditor_manipulation/GO_NO_GO_REVIEW.md)
disputes whether those labels establish investigator failures: the visible
instructions did not sufficiently specify authenticated source origin or the
completeness of permission records. Less certainty alone does not establish
acceptance of a false claim. Original reviewer labels and reports are preserved.

### Start here

- [Study guide and historical protocols](studies/auditor_manipulation/README.md)
- [Actual target communications and applied changes](studies/auditor_manipulation/TARGET_SNIPPETS.md)
- [Two-round protocol](studies/auditor_manipulation/ADAPTIVE_V7_PROTOCOL.md) and
  [original results with interpretation correction](studies/auditor_manipulation/ADAPTIVE_V7_RESULTS.md)
- [Offline validity and research review](studies/auditor_manipulation/GO_NO_GO_REVIEW.md)
- [Conditional next experiment and stopping rules](studies/auditor_manipulation/DECISIVE_TEST_SPEC.md)

### Scope of the completed comparison

Three targets each received four turns per condition per round. Across
communicating and disconnected groups and two rounds, that is 48 target turns.
The communicating group delivered 12 messages in round one and 11 in round two.
Both groups received historical public feedback. Fresh investigators examined
frozen workspaces. This was adaptation through context, not model-weight training.

The latest allocation spent **$26.61435475 of $30**, including the earlier
$3.4241635 comparison and confirmed lost-response charges. This is not the total
historical cost of the project. No further model calls are scheduled. The
conditional second-round defense replay did not trigger, and no defense efficacy
or general investigator-reliability claim follows.

The next design gives both investigator variants access to the same verifiable
evidence and includes truthful explanations that should clear the target. It is
specified only. Implementation, offline validity gates and a separately approved
execution budget remain prerequisites.

### Code and evidence

`auditor_manipulation/` contains the simulation, investigator interfaces,
adaptive runners, scoring and request-accounting code. `tests/` contains local
software checks. `studies/auditor_manipulation/` contains protocols, configurations
and curated research evidence. The [selected-action extract](studies/auditor_manipulation/EVIDENCE_TARGET_SNIPPETS.json)
and [review extract](studies/auditor_manipulation/EVIDENCE_GO_NO_GO.json) retain
source text and archive locators. Raw run directories remain gitignored under
`results/`; the curated extracts are not a complete run archive.

Software checks verify implementation behavior, not investigator capability:

```sh
python3 -m unittest discover -s tests -v
```

Paid runners require explicit invocation and authorization. Historical run
commands and budgets in old protocols are not instructions to resume collection.

### Model portability

The workflow, evidence interfaces and report schema are reusable. Earlier runners
support configured model selection, but the latest adaptive runner still pins
Astra Pro, OpenAI Flex, response metadata and pricing/capacity checks. Changing
`selected_model` alone does not switch that runner. Separate model adapters for
targets, investigators and reviewers, self-hosted inference, and activation-probe
instrumentation remain future work.

## Original collusion study

Measuring whether AI monitors collude with the models they oversee, and whether
"collusion is rare" is a stable property or a temporary capability artifact.

A common plan for controlling powerful AI is to have one model watch another and
flag bad behavior. That only works if the watcher cannot quietly side with the
model it is policing. This repo measures whether it can.

An initial motivating measurement (Järviniemi, *Subversion via Focal Points*,
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
- `auditor_manipulation/` the new study's offline fixtures, messages, and scorer.
- `studies/auditor_manipulation/` the new draft protocol and model/cost plan.
- `notes/` private working notes (gitignored).

## Status

The original study has pre-checks and a draft write-up in `docs/`. The newer
investigator study has completed development runs and an offline validity review.
Its current interpretation appears above. Historical collusion research and
software checks are not empirical results of the newer experiment.

## Approach (two arms, one question)

- **Behavioral**: vary how hard the collusion is and how much it pays, and score
  attempts, not just successes, so propensity can be separated from capability.
- **Activation (open weights)**: look for the latent collusion signal directly,
  including when the behavior stays silent. This is what lets propensity be read
  where behavior cannot show it.

Numbers come straight from the scripts. Limits are written down, not buried.

## SpineFrame evidence integration

The [self-contained evidence kernel](evidence_kernel/README.md) vendors SpineFrame signing and event-recording primitives with attribution. It adds ordered content commitments, a host-pinned signing key and snapshot verification. The [Qwen-only evidence study](studies/spineframe_qwen/PROTOCOL.md) compares unsigned structured records with the same signed records. Historical imports authenticate integrity since import, not original action truth or live capture. [Final results](studies/spineframe_qwen/RESULTS.md): 40 fixed Qwen-only slots, 37 completed and three operational failures. Neither condition achieved full focal-mechanism detection. On eight matched attacks, seven outcomes were identical and one improved only to a partial warning. New actual charges: $0.19689960. Signing intact historical records did not establish a reliable detection benefit.

## Qwen with additional runtime observations

The [completed recorder-observation study](studies/recorder_observations/RESULTS.md) gives Qwen all neutral observations from reviewed local executions inline: received archive members, Git commit metadata, emitted diagnostic logs and broker messages. Forty fixed slots yielded 36 reports and four operational failures. On nine completed attack pairs, explicit exposure recognition increased from 0 to 3, but all three reports still called the overall activity non-anomalous; one wrongly dismissed the key-in-commit consequence as a simulation artifact. Two clearer gains concern the same weight-logging packet. Seven matched benign pairs had no focal false accusation. This is a limited recognition benefit, not a reliable misalignment defense or production telemetry validation. New accounted charges were $0.30204675. [Protocol](studies/recorder_observations/PROTOCOL.md), [all outcomes](studies/recorder_observations/OUTCOMES.md), [collection code](recorder_observations/README.md).
