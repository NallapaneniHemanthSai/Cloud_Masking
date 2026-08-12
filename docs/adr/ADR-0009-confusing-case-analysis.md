# ADR-0009 — Confusing-Case & Failure-Analysis Strategy

- **Status:** ACCEPTED (2026-08-12)
- **Milestone:** M9 (Confusing-Case Evaluation & Failure Analysis)
- **Related:** ADR-0008 (evaluation), ADR-0001 (datasets), Charter §3.1 (haze), NT-1/2/3, Risk R-07, R-16

## Decision

Build a **failure-analysis layer on top of the M8 evaluation primitives** (confusion matrix, per-class
metrics) that **explains** model failures rather than repeating metrics. It categorises errors with a typed
taxonomy, computes pixel- and sample-level error statistics **by reusing M8 primitives (no duplicated
metric math)**, deterministically ranks the hardest cases, stratifies failures (thin cloud always visible),
and emits reports + backend-independent visualization specs. Categories that require information not present
in the current pipeline are marked **DEFERRED / NOT MEASURABLE** — never fabricated.

## Purpose of failure analysis

Answer, when the model is wrong: **what kind of case caused it**, **which class**, **FP vs FN vs class
confusion**, **which samples are hardest**, **how severe**, **where failures concentrate** (thin/thick
cloud, shadow, clear), and **enable later visual inspection**. This is distinct from M8 (which answers
"how good") — M9 answers "how, where, and on what it fails".

## Confusing-case taxonomy & measurability

| Category | Measurability | Basis / why |
|----------|---------------|-------------|
| FALSE_POSITIVE | **MEASURABLE** | pred = c, true ≠ c (from confusion). |
| FALSE_NEGATIVE | **MEASURABLE** | true = c, pred ≠ c. |
| CLASS_CONFUSION | **MEASURABLE** | true = c → pred = c′ (off-diagonal). |
| CLEAR_SURFACE_FAILURE | **MEASURABLE** | errors where true class = clear. |
| THICK_CLOUD_FAILURE | **MEASURABLE** (multiclass) | errors where true = thick cloud. |
| THIN_CLOUD_FAILURE | **MEASURABLE** (multiclass) | errors where true = thin cloud. |
| CLOUD_SHADOW_FAILURE | **MEASURABLE** (multiclass) | errors where true = cloud shadow. |
| EDGE_ERROR | **DEFERRED** | needs boundary (morphological) analysis of mask arrays — not computed by default. |
| SMALL_OBJECT_FAILURE | **DEFERRED** | needs connected-component analysis — not computed by default. |
| HIGH_CONFIDENCE_ERROR | **NOT MEASURABLE** | requires predicted probabilities; the pipeline stores labels, not probabilities. |
| LOW_CONFIDENCE_ERROR | **NOT MEASURABLE** | same as above. |

A category is **never claimed measurable unless the available prediction/metadata supports it.** The
measurability of every category is recorded in every analysis result and report.

## Error definitions

- **False positive (class c):** pixels predicted `c` whose true class ≠ `c`.
- **False negative (class c):** pixels of true class `c` predicted as something else.
- **Class confusion (c → c′):** a wrong pixel with true `c`, predicted `c′` (c ≠ c′).
- **Per-class failure (class X):** the set of errors whose **true** class is `X` (FN of X), surfaced so
  thin-cloud failures are directly visible.

## Pixel-level vs sample-level analysis

- **Pixel-level:** derived from an `EvaluationResult`/`ConfusionMatrix` (M8) — always available. Per class:
  FP, FN, support, error rate, dominant confusion target.
- **Sample-level:** requires **per-sample predicted + target label arrays**. When provided, each sample's
  error count/rate, per-class error breakdown, dominant confusion pair, and triggered categories are
  computed (reusing a per-sample `ConfusionMatrix`). When sample data is absent, sample-level analysis is
  simply empty (documented), not fabricated.

## Severity ranking

Evidence-based only. Severity is assigned from the **error rate** (the only signal available without
probabilities), with configurable thresholds: `CRITICAL ≥ 0.75`, `HIGH ≥ 0.5`, `MEDIUM ≥ 0.25`, `LOW > 0`,
`NONE = 0`. **Confidence-based severity is unavailable** (no probabilities): `HIGH/LOW_CONFIDENCE_ERROR`
remain NOT MEASURABLE, and confidence is **not** inferred from logits (no such method is defined here).

## Stratification strategy

Failure summaries by **dataset · split · true class · predicted class · error type**. CloudSEN12 exposes
**clear / thick cloud / thin cloud / cloud shadow** explicitly (thin cloud directly visible). On Cloud N
stays **binary** — the CloudSEN12 taxonomy is **never** auto-applied to On Cloud N. Haze is **not** a
category (approximated under thin cloud; Charter §3.1).

## Sampling strategy

Analysis runs over the **samples provided for a single split** (no cross-split mixing). It **identifies**
hard examples only — it never oversamples or duplicates them for training.

## Top-K policy

Deterministic top-K by a chosen criterion (`error_rate`, `error_count`, per `class`, per `error_type`).
K is configuration-controlled. Deduplication by `sample_id` happens **before** top-K so a sample cannot
occupy multiple slots.

## Duplicate handling

Records are **deduplicated by `sample_id`** (patch-level entries group to their base sample id); the
**worst** entry per sample is kept (deterministic). A sample appears **once** per ranked list. Split
boundaries are preserved — the analyzer **refuses to mix splits** (raises if a sample's split ≠ the
configured split).

## Reproducibility

Analysis is **deterministic**: fixed error definitions + a documented total-order ranking (see below) +
`config_hash` + `FAILURE_ANALYSIS_VERSION`. No randomness in the analysis itself (any synthetic data in the
CLI/tests is separately seeded).

**Ranking total order (documented tie-break):** 1) severity (CRITICAL→LOW), 2) error_rate (desc),
3) error_count (desc), 4) `sample_id` (ascending). This yields a stable, reproducible ordering.

## Privacy / data handling

**No raw tensors** are stored in records — only counts, rates, ids, class names, and **path/id references**
(`source_reference`). Reports carry no pixel data.

## Report format

**JSON / CSV / Markdown** via the reused `app.visualization.reports.Report` (no duplicated serialisation).
Reports include analysis + evaluation versions, model/dataset/split, the **taxonomy with measurability**,
failure counts, class + error-type summaries, top-K hard examples, and an explicit **limitations** section
labelling `NOT MEASURABLE` / `DEFERRED` / `NOT YET MEASURED`.

## Visualization integration

Confusing-case visualization is emitted as **backend-independent `FigureSpec`s** (reusing M5): ground
truth, prediction, error overlay, class legend, plus error category / severity / sample metadata in the
spec options. **matplotlib is never imported into the failure-analysis core** — rendering stays behind the
M5 backend abstraction.

## Limitations

Confidence-based categories, edge errors, and small-object failures are **deferred/not measurable** with
current data. Sample-level analysis needs per-sample predictions. **No real dataset/predictions exist yet**
— all figures produced this milestone are synthetic and are labelled **NOT YET MEASURED**.

## Trade-offs

Reusing M8 confusion primitives avoids duplicated math and guarantees consistency, at the cost of being
limited to what confusion counts expose (no spatial/confidence categories). This is the honest trade —
deferring what cannot be measured beats fabricating it.

## Consequences

`app.failure_analysis` depends on `app.evaluation` (primitives) and `app.visualization` (specs) — not on
models/training/inference. Its outputs feed later hard-example curation and NT-1/2/3 fixtures without any
training change in this milestone.

## Future improvements

Confidence categories via calibrated probabilities; edge metrics (boundary bands); small-object analysis
(connected components); real-data failure statistics with per-sample predictions; wiring hard examples into
targeted evaluation of NT-1/2/3.
