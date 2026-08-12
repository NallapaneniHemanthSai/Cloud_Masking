# ADR-0008 — Evaluation Strategy

- **Status:** ACCEPTED (2026-08-10)
- **Milestone:** M8 (Evaluation)
- **Related:** ADR-0001 (datasets), ADR-0006 (model), ADR-0007 (training), KPIs (`06_KPI_ACCEPTANCE.md`),
  Charter §3.1 (haze), Risk R-07 (aggregate hides subgroup), R-16 (thin-cloud imbalance)

## Decision

Implement a **confusion-matrix-based, per-class-first** segmentation evaluation framework that reports
overall, **per-class**, macro, micro, and weighted metrics plus **stratified** results — designed so a
strong overall score can **never conceal poor per-class (especially thin-cloud) performance**. Undefined
metrics are represented **explicitly** (never silent zeros). No model/training/inference/deployment/API code.

## Evaluation objectives

Answer, for every evaluation: how well the model detects **cloud overall**, **clear**, **thin cloud**,
**thick cloud**, and **cloud shadow**; **which classes are confused** (confusion matrix); and **where
performance degrades** (per-class + stratified). Overall metrics are necessary but **per-class and
stratified metrics are mandatory** (quality requirement).

## Metric selection

**IoU/Jaccard, Dice, Precision, Recall, F1, Pixel Accuracy** — the spec's required set. Each is computed
**per class** and aggregated (macro / micro / weighted). Mathematical definitions per class from confusion
counts (TP/FP/FN):

- IoU = TP / (TP + FP + FN)
- Dice = 2·TP / (2·TP + FP + FN)   (equals per-class F1)
- Precision = TP / (TP + FP)
- Recall = TP / (TP + FN)
- F1 = 2·P·R / (P + R)
- Pixel Accuracy = Σ diag / Σ all   (global)

## Binary vs multiclass evaluation

Two **separate, non-mixed** modes:

- **Binary** (On Cloud N benchmark): `num_classes = 2` → `0 = non_cloud`, `1 = cloud`.
- **Multiclass** (CloudSEN12): `num_classes = 4` → `0 = clear`, `1 = thick_cloud`, `2 = thin_cloud`,
  `3 = cloud_shadow` (verified in M3).

Binary and 4-class metrics are **never combined**. A documented, **opt-in** label-collapse utility exists
for deliberately viewing CloudSEN12 as cloud-vs-clear, but it is never applied automatically.

## Macro vs micro aggregation

- **Macro** = unweighted mean over **defined** classes. Every class (incl. thin cloud) counts **equally**,
  so a rare, poorly-detected class is not hidden by a dominant class. Undefined classes are **excluded**
  and the count of included classes is recorded.
- **Micro** = computed from **globally summed** TP/FP/FN across classes. For single-label segmentation this
  equals pixel accuracy (documented).
- **Weighted** = mean weighted by per-class support (true-pixel count); absent classes contribute zero
  weight.

## Per-class aggregation

Every class's metrics are **always computed and reported** (`ClassMetrics`), so thin-cloud performance is
always visible regardless of the aggregate.

## Absent-class handling

A class absent from both prediction and ground truth (TP=FP=FN=0) yields **undefined** IoU/Dice/… A class
absent from ground truth yields **undefined recall**; no predicted positives yields **undefined precision**.
These are represented as `MetricValue(value=None, defined=False, reason=…)`, **not zero**, and excluded from
macro/weighted averages. **Undefined values are never silently converted to misleading zeros.**

## Confusion-matrix strategy

A multiclass **pixel-level** confusion matrix with **rows = ground truth (true)**, **columns = predicted**.
Configurable class count and **ignore label** (ignored pixels excluded before counting). Accumulation is
deterministic (exact integer counts via `bincount`). Serialised as a nested integer list (no tensors).
Per class: `TP = M[c,c]`, `FP = Σ_r M[r,c] − TP`, `FN = Σ_c' M[c,c'] − TP`, `TN = total − TP − FP − FN`.

## Threshold / argmax policy

- **Multiclass:** predicted label = `argmax` over the class channel of logits/probabilities.
- **Binary:** `argmax` over 2 classes (equivalently threshold 0.5 on the cloud probability, documented).
- Inputs may be class-index arrays **or** logits; a helper converts logits → labels. Targets are class-index
  arrays.

## Batch aggregation strategy

**Accumulate sufficient statistics (confusion counts) across all batches first, then compute metrics
once.** Averaging per-batch metrics is **wrong** because a ratio of sums ≠ a mean of ratios (e.g. IoU over
two batches with different class supports). The framework therefore sums confusion matrices and derives
metrics from the total. A test proves `metric(accumulate(b1)+accumulate(b2)) == metric(accumulate(all))`.

## Dataset split policy

Evaluation runs on a **named split** (e.g. `val`, `test`) recorded in the result. Leakage-resistant spatial
holdout is enforced upstream (M4 splitting, NFR-4/AC-3); evaluation records **which split** was used.

## Stratified evaluation strategy

Always produce **Overall** + per-class strata **Clear / Thick Cloud / Thin Cloud / Cloud Shadow**
(from the per-class metrics), plus optional breakdown by **dataset / split / sample group** (region/season
arrive with real data). **Haze is NOT a class** — it is approximated under thin cloud and has **no
standalone KPI** (Charter §3.1). Thin-cloud performance is always surfaced.

## Reproducibility

Evaluation is **deterministic**: integer confusion counts + fixed metric formulas → identical outputs for
identical inputs. Every record carries a deterministic `config_hash` and `EVALUATION_VERSION`.

## Metric serialization

Typed dataclasses serialise to dict/JSON; **no raw tensors** are stored; undefined metrics serialise as
`null` with a reason. Confusion matrices serialise as nested integer lists.

## Report generation

Reports in **JSON / CSV / Markdown** (reusing the existing `app.visualization.reports.Report` model — no
duplicated serialisation logic), including model, dataset, split, overall/per-class/macro/micro metrics,
confusion matrix, stratified results, config hash, evaluation version, and timestamp.

## Confidence / uncertainty strategy (DEFERRED)

**Confidence intervals / uncertainty estimation are DEFERRED.** The KPIs specify 95% CIs on real-data
runs; those are computed once real evaluation data exists (later milestone). M8 records **point metrics
only** and **does not fabricate** confidence estimates. This deferral is recorded here explicitly.

## Failure handling

Empty masks → all-undefined metrics (explicitly). Ignored pixels excluded before counting. Shape mismatch,
out-of-range labels, or a class-count mismatch raise `EvaluationError`. No undefined value is coerced to a
number.

## Trade-offs

- Confusion-first design costs a little memory (K×K counts) but guarantees correct global aggregation and
  full per-class visibility — the right trade for the "no hiding" requirement.
- Explicit undefined values add branching but prevent the misleading-zero failure mode (R-07).

## Consequences

- `app.evaluation` exposes metrics/confusion/aggregation/stratification/runner/report/records — reusable,
  serialisable, deterministic. It does **not** modify `app.training`; results integrate via a clean adapter
  (an optional evaluation callback interface) that later milestones (checkpoint selection, benchmarking) use.

## Future improvements

- 95% confidence intervals / bootstrap uncertainty on real-data runs.
- Boundary/edge metrics for thin-cloud edges; calibration; cross-region/season strata with real metadata.
- Optional evaluation callback wired into training checkpoint selection (M-later).
