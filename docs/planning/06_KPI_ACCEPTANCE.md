# KPIs, Acceptance Conditions & Negative Tests

> **Deliverable ID:** D1 (partial) / D5 (plan) · **Milestone:** M1 · **Status:** DRAFT for approval
> **All baseline and achieved values below are `NOT YET MEASURED`.** They are populated only from our own
> runs, in Milestones 7–11 (baselines/O2) and 10–11 (candidate/O3), never fabricated.

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

## 4. Pass Contract

The project passes only when **every** KPI target passes under AC-1 & AC-4, **every** guardrail holds, and
**all five** negative tests pass — with independent acceptance evidence (AC-3). Otherwise the project is
explicitly **held or revised** with documented rationale. Averages never override subgroup failures.
