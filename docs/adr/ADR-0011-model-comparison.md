# ADR-0011 — Controlled Model Comparison

- **Status:** ACCEPTED (2026-08-12)
- **Milestone:** M11 (Controlled Baseline vs Improved Model Comparison)
- **Related:** ADR-0010 (Attention U-Net), ADR-0006 (baseline U-Net), ADR-0002 (compute/MPS envelope),
  ADR-0007 (training), ADR-0008 (evaluation), ADR-0009 (failure analysis); Objective O3; KPI-1/2;
  Risk R-02, R-15, R-16, R-17

## Decision

Add a dedicated `app.comparison` package that performs a **controlled, honest** baseline-vs-improved
comparison (U-Net vs Attention U-Net) by **reusing** the existing engines — the M7 `Trainer` (no second
training engine), the M8 `EvaluationRunner` (no second metrics system), and the M9 `analyze_failures`
(no second failure framework). The comparison contributes only: a single-source `ComparisonConfig`,
fairness guardrails, quality/compute records, a thin-cloud-primary decision framework, a canonical
`ModelComparisonArtifact`, a `compare_models` CLI, and reports/viz-specs. **No performance is claimed:
real controlled results are NOT YET MEASURED, so the decision is INCONCLUSIVE.**

## Primary question (not "who scores higher")

> *Does Attention U-Net provide a meaningful improvement over the baseline U-Net — particularly for
> thin-cloud and other difficult failure cases — for a reasonable computational cost?*

Attention U-Net is **not** assumed to win. Overall accuracy alone is explicitly rejected as the criterion.

## Fairness by construction, then verified

Both arms are **derived from one `ComparisonConfig`** via `plan_for()`, so every shared control (dataset,
dataset/preprocessing version, patch size, normalization, augmentation, split, seed, batch size, epochs,
optimizer, scheduler, loss, class weighting, checkpoint/early-stopping policy, device, training budget) is
identical by construction — the model architecture/config is the **only** intentional difference. The
`guardrails.check_fairness` then **re-verifies** this field by field and raises `GuardrailViolation` on any
non-architectural mismatch (or if both arms share one architecture). Two hashes are exposed:
`fairness_hash` (shared controls only; identical for both arms) and `config_hash` (whole comparison).

## Quality separated from compute cost

The comparison never collapses to a single score. `MetricComparison` carries per-class + macro/micro/
weighted deltas with **thin cloud surfaced explicitly** (IoU/Dice/Recall + false-negatives); `ComputeMeasurement`/`ComputeComparison`
carry parameters (MEASURED), timings, and — honestly —
`peak_memory = NOT_MEASURED` on cpu/mps (never inferred from parameter count). FLOPs remain DEFERRED.

## Decision framework

`decision.decide` returns one of **IMPROVED / NO_SIGNIFICANT_IMPROVEMENT / REGRESSION / INCONCLUSIVE /
COMPUTE_UNJUSTIFIED**, considering (in priority) thin-cloud IoU/Dice, macro performance, worst-class
behaviour, M9 failure behaviour, compute cost, and reproducibility (seed count). Rules encode the
milestone's guardrails:

- A stronger aggregate that **hides thin-cloud degradation is a REGRESSION**, not an improvement.
- A **slight thin-cloud gain at substantial compute cost is COMPUTE_UNJUSTIFIED** (flag the trade-off).
- **Without real controlled results (or on synthetic data) the verdict is INCONCLUSIVE** — never a
  guessed winner (see Honesty).
- Fewer than two seeds ⇒ statistical significance `NOT_MEASURED` (no fabricated confidence intervals).

## Honesty (measurement status on every quantity)

Every value keeps a status: `MEASURED` (real), `SYNTHETIC` (produced on synthetic data — VALIDATION
ONLY, not a benchmark), `NOT_MEASURED` (unavailable, e.g. peak memory on cpu/mps), `NOT_YET_MEASURED`
(awaiting real dataset experiments), `DEFERRED` (e.g. FLOPs). IoU/Dice/F1/time/memory/significance are
never invented. The synthetic smoke path trains both real architectures on small synthetic tensors so the
full M7→M8→M9 pipeline and compute are genuinely exercised (compute MEASURED), while quality stays
SYNTHETIC and the decision stays INCONCLUSIVE.

## Data policy

Real experiments require a real **processed** CloudSEN12 dataset present locally; the runner checks for it
and **never downloads** (On Cloud N redistribution restrictions respected — ADR-0001). Absent real data,
real-data quality is `NOT_YET_MEASURED`. Only the intended seed matrix (seeds 1/2/3) rows actually
executed are marked as run.

## Alternatives rejected

- **Single aggregate "winner" score** — hides thin-cloud regressions; rejected (the whole point of O3).
- **A second, comparison-specific training/eval loop** — would risk divergence from M7/M8 and unfair
  comparisons; rejected in favour of reuse.
- **Fabricated/synthetic results labelled as benchmarks** — rejected outright (section 21 honesty rule).

## Consequences

`app.comparison` adds typed config/guardrails/records/metrics/failures/decision/runner/viz-specs/report/
serialization modules, a `ModelComparisonArtifact` with deterministic content hashing (timestamps/notes
ignored), a `compare_models` CLI (`--synthetic-smoke`), tests + a framework-free manual harness, and
`COMPARISON_VERSION = 0.11.0`. Training (M7), evaluation (M8), failure analysis (M9), and the model
architectures (M6/M10) are **unchanged**.

## Future work

Execute the real seed-matrix comparison once the processed dataset exists (populates KPI-1/2 for O3 with
95% CIs and a defensible verdict); optional additional comparison models (DeepLabV3+/UNet++); MPS/CUDA
peak-memory capture; FLOP measurement once a reliable dependency-light method is chosen.
