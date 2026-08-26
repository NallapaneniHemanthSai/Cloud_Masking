# KPIs, Acceptance Conditions & Negative Tests

> **Deliverable ID:** D1 (partial) / D5 (plan) · **Milestone:** M1 · **Status:** DRAFT for approval
> **All baseline and achieved values below are `NOT YET MEASURED`.** They are populated only from our own
> runs, in Milestones 7–11 (baselines/O2) and 10–11 (candidate/O3), never fabricated.
> **Prerequisite (M12):** these KPIs can only be populated once a real experimental dataset passes the M12
> `is_experiment_ready()` gate (verified files/checksums/labels, disjoint scene-grouped splits, thin-cloud
> present, train-only normalization).
> **First real measurement (2026-08-20):** a real **CloudSEN12+** subset now passes that gate and a first
> **real** U-Net vs Attention U-Net comparison ran on MPS (see `docs/comparison/real_experiment_cloudsen12.md`).
> That run is a **bounded first experiment** (32 samples, one small config, 12 epochs, 3 seeds) — **not** the
> frozen AC-4 acceptance benchmark — so the formal KPI values below **remain NOT YET MEASURED**. The bounded
> run's measured signal (thin-cloud IoU mean +0.050 for Attention U-Net, with a cloud-shadow trade-off →
> overall MIXED) is recorded there, explicitly separate from these acceptance KPIs.

---

## 1. Acceptance Conditions (AC)

| ID | Name | Definition |
|----|------|------------|
| **AC-1** | Representative operation | Validate stratified performance across regions and seasons. |
| **AC-2** | Boundary & failure operation | Exercise: overall accuracy dominated by easy pixels; snow masked as cloud; thin cloud leaking into analysis. |
| **AC-3** | Independent acceptance evidence | Spatially disjoint areas, verified CRS, authoritative/field reference evidence; reserved **before** O3 tuning. |
| **AC-4** | Frozen resource envelope | Same versions, workload, hardware/facility limits, resource budget for reference and final comparisons. |

## 2. KPI Table

Baseline is the **O2 reference measured on the same evidence and resource envelope**. Until O2 is measured,
baselines are unknown → `NOT YET MEASURED`.

| ID | Measure | Direction | Unit | Target / pass rule | Conditions | Baseline (O2) | Achieved (O3) |
|----|---------|-----------|------|--------------------|------------|---------------|---------------|
| **KPI-1** | Accuracy on confusing cases | higher better | % | ≥ O2 + 3 pp, **or** within 1 pp while improving primary resource KPI by ≥ 20%. | AC-1, AC-3 | NOT YET MEASURED | NOT YET MEASURED |
| **KPI-2** | Overall masking accuracy | higher better | % | ≥ O2 + 3 pp, or within 1 pp while improving resource KPI by ≥ 20%. | AC-1, AC-3 | NOT YET MEASURED | NOT YET MEASURED |
| **KPI-3** | Downstream change-detection error | lower better | 0–100 rubric score (frozen before O2) | ≥ 80/100 **and** ≥ 5 points better than O2 reference. | AC-1, AC-3 | NOT YET MEASURED | NOT YET MEASURED |
| **KPI-4** | Independent-area validation coverage | higher better | % | ≥ 95% (100% for safety/compliance-critical items). | AC-1, AC-3 | NOT YET MEASURED | NOT YET MEASURED |
| **KPI-5** | Cross-region performance gap | lower better | % | ≤ 0.80 × O2 reference; no critical condition worse than reference. | AC-1, AC-3 | NOT YET MEASURED | NOT YET MEASURED |
| **KPI-6** | Registration / spatial-alignment error | lower better | pixels | ≤ 0.80 × O2 reference; no critical condition worse than reference. | AC-1, AC-3 | NOT YET MEASURED | NOT YET MEASURED |

**Measurement method (all KPIs):** use the leakage-resistant independent spatial partition; report
condition-wise values, **95% confidence intervals**, and the raw confusion/error evidence.

**Guardrail (all KPIs):** *No critical subgroup, scene, or operating condition may be hidden by an aggregate
result.* A run that passes on average but fails a critical subgroup is a **fail**.

**KPI-3 rubric requirement:** Before O2, freeze a 0–100 rubric with ≥ 5 observable criteria and named
0 / 50 / 80 / 100 anchors; use **two independent raters** and report agreement + condition-wise scores.
→ The rubric will be authored and frozen at the start of Milestone 8 (before O2 is finalised).

**Haze:** there is **no standalone haze KPI**. Haze is approximated within the thin-cloud class and reported
qualitatively inside the thin-cloud stratum of KPI-1 (see Charter §3.1, `01_REQUIREMENTS.md` §8, AS-02).

## 2a. Engineering KPIs (realistic project targets)

These are **engineering targets set at planning time** (not measurements). Each has a target value,
measurement method, evidence source, and a current status. All are **NOT YET MEASURED**. Segmentation-quality
targets refer to the **cloud class(es) on the independent spatial holdout** (AC-3); resource/latency targets
refer to the frozen `full` profile on Apple Silicon (MPS) at 512×512 patch unless noted.

| ID | Metric | Target | Measurement method | Evidence source | Status |
|----|--------|--------|--------------------|-----------------|--------|
| **KPI-E1** | IoU (cloud class, mean over cloud classes) | **≥ 0.75** | TorchMetrics `JaccardIndex`, per-class then mean, on spatial-holdout test set. | Evaluation run + MLflow artifact (confusion matrix). | NOT YET MEASURED |
| **KPI-E2** | F1-score (cloud) | **≥ 0.85** | TorchMetrics `F1Score` (per-class), spatial-holdout. | Evaluation report. | NOT YET MEASURED |
| **KPI-E3** | Precision (cloud) | **≥ 0.85** | TorchMetrics `Precision`, spatial-holdout. | Evaluation report. | NOT YET MEASURED |
| **KPI-E4** | Recall (cloud) — incl. **thin-cloud recall guardrail ≥ 0.70** | **≥ 0.85** overall; thin-cloud **≥ 0.70** | TorchMetrics `Recall`, per-class + thin-cloud subgroup. | Stratified evaluation report. | NOT YET MEASURED |
| **KPI-E5** | Mean inference latency | **≤ 2.0 s** / 512×512 patch (MPS); ≤ 5.0 s CPU fallback | Median of ≥ 50 single-patch forward passes, warm model, timed in `services/prediction`. | Benchmark script log + `/metrics`. | NOT YET MEASURED |
| **KPI-E6** | Peak inference memory | **≤ 4 GB** | Process RSS / MPS allocator peak during single-image inference. | Benchmark log. | NOT YET MEASURED |
| **KPI-E7** | Frontend response time (non-inference UI actions) | **≤ 500 ms**; prediction round-trip shows progress within **300 ms** | Browser performance timing on dashboard/history/compare actions against local API. | Frontend perf log / manual measurement. | NOT YET MEASURED |

> Note: KPI-E1..E4 are **quality** targets; because of thin-cloud class imbalance (R-16), **per-class IoU/F1
> and thin-cloud recall** are authoritative — **pixel accuracy alone is never used to claim success** (NT-1).
> The spec-mandated KPI-1..6 (§2) remain the primary acceptance gate; KPI-E1..E7 are supporting engineering
> targets. If a supporting target proves unrealistic on the frozen MPS envelope, it is revised with rationale
> (not silently dropped) and the revision is recorded here.

## 3. Mandatory Negative Tests (NT) — all five must pass

| ID | Failure condition | Expected safe behaviour | Recovery | Milestone |
|----|-------------------|-------------------------|----------|-----------|
| **NT-1** | Overall accuracy dominated by easy pixels. | Detect; abstain or enter degraded mode; label affected result; prevent silent use outside validated envelope. | Restore accepted data/coord/model versions; regenerate affected layer; reconcile with authoritative evidence. | M9 |
| **NT-2** | Snow masked as cloud. | Same detect/abstain/label/prevent. | Same. | M9 |
| **NT-3** | Thin cloud leaking into analysis. | Same. | Same. | M9 |
| **NT-4** | A map hides uncertainty, missing coverage, or unsuitable resolution. | Same — surface uncertainty/coverage/resolution; do not present a misleading map. | Same. | M12/M14 |
| **NT-5** | Field/authoritative observations do not support the inference. | Detect invalid record/state **before silent commit**; replay is idempotent; lineage remains complete. | Same. | M15 |

Each NT retains: fixture/sample ID · precondition · version & config · expected vs observed · logs/measurements ·
recovery time · residual-risk decision.

> **M16 status (2026-08-26):** the **D5 acceptance harness** (`app.acceptance`, `run_acceptance.py`,
> `GET /acceptance`) proves **all five NTs on deterministic SYNTHETIC fixtures** — each with a pass fixture
> (must not fire) and a fail fixture (must fire → NT-1..4 drive M15 degraded mode + recovery; NT-5 rejects the
> invalid record before commit). It reuses M8 confusion + M15 degraded/recovery/lineage (no duplicate system).
> Verdict: **SAFETY = PASS (synthetic)**. It does **not** compute real KPIs — the KPI table above and AC-1/AC-3/
> AC-4 acceptance remain **NOT YET MEASURED** (need a real frozen-envelope dataset), so the full **Pass Contract
> is not yet satisfiable**; the harness reports this honestly. The M11 real-data conclusion remains **MIXED**.

## 4. Pass Contract

The project passes only when **every** KPI target passes under AC-1 & AC-4, **every** guardrail holds, and
**all five** negative tests pass — with independent acceptance evidence (AC-3). Otherwise the project is
explicitly **held or revised** with documented rationale. Averages never override subgroup failures.
