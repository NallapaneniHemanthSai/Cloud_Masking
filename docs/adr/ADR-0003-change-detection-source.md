# ADR-0003 — Change-Detection Evaluation Source

- **Status:** DEFERRED (decision to be made in Milestone 12)
- **Milestone:** raised M1, decided M12
- **Related:** O4, FR-4, KPI-3, Risk R-06, claim C-4, Assumption AS-03

## Context

O4 requires quantifying the **downstream impact of masking errors on a change-detection task**. This needs a
bi-temporal source whose "change" signal is measurably affected by cloud-masking errors. The candidate is
**OSCD (Onera Satellite Change Detection)** — Sentinel-2 bi-temporal pairs with change annotations. Risk: OSCD
scenes may not spatially/temporally overlap the CloudSEN12 cloud scenes, weakening the O4 linkage.

## Options (to be evaluated in M12)

1. **OSCD** as the change-detection dataset, with cloud masks applied to its image pairs.
2. **Controlled synthetic bi-temporal fixture** — construct paired scenes with known ground-truth change and
   **inject cloud-masking errors** to measure their propagation (fully controllable, no overlap dependency).
3. **Hybrid** — OSCD for realism + synthetic fixtures for controlled sensitivity/ablation.

## Decision

**Deferred.** Default fallback if OSCD overlap is insufficient: **Option 2 (controlled synthetic fixture)**,
which guarantees a measurable masking-error → change-error relationship regardless of dataset overlap. Final
choice recorded here at M12 with evidence.

## Consequences

- Keeps O4 feasible even if OSCD proves unsuitable (R-06 mitigated).
- KPI-3's frozen 0–100 rubric must be authorable against whichever source is chosen; the rubric is frozen in M8
  independent of this decision.

## Reference

Daudt, R.C. et al. "Urban Change Detection for Multispectral Earth Observation Using Convolutional Neural
Networks" (OSCD), IGARSS 2018. *(Citation to be verified and added to `paper/` in M12/M19.)*
