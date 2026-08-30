# Ablation Study — Template

**Milestone 19 · Deliverable D7.**

> ## ⚠ STATUS: EVERY ABLATION BELOW IS **NOT EXECUTED**
>
> This project has run **one** controlled experiment (M11: U-Net vs Attention U-Net, 3 seeds, bounded
> 32-sample subset). No ablation has been performed. This document is a **specification** of the
> ablations that would be run, with result columns deliberately left as `NOT EXECUTED`.
>
> A fabricated ablation table would be misconduct (ADR-0019 §5). An honestly empty template is a
> contribution: it states precisely what remains to be done and how.

---

## Common protocol (applies to every ablation below)

Inherited from the M11 fairness guardrails ([ADR-0011](../docs/adr/ADR-0011-model-comparison.md)) — a
single factor varies; everything else is pinned.

| Control | Fixed value |
|---|---|
| Dataset | CloudSEN12+ L1C expert-labelled subset, `dataset_version` recorded |
| Split | ROI-grouped, class-stratified, `leakage_ok = True` |
| Normalization | min–max, fit on **train only** |
| Patch / batch | 128 px / 8 |
| Optimizer / scheduler | AdamW / cosine |
| Device | recorded per run (MPS or CPU); never compared across devices |
| Seeds | **≥ 3** (ADR-0011: fewer than 2 ⇒ significance `NOT_MEASURED`) |
| Primary metric | **thin-cloud IoU** |
| Secondary metrics | per-class IoU/Dice/recall, macro IoU, worst-class IoU, M9 failure counts |
| Guardrail | worst-class regression is reported, never averaged away |
| Reporting | per-seed values **and** consistency count (e.g. "3/3"), not just the mean |

**Execution path (already built — no new engine required):**

```bash
backend/.venv/bin/python backend/scripts/run_real_comparison.py \
    --epochs 12 --batch 8 --device mps --seeds 1 2 3 \
    [ablation-specific flags]
```

---

## A1 — Attention gates on / off *(the core ablation)*

| Field | Value |
|---|---|
| **Question** | Is the thin-cloud gain attributable to the attention gates specifically? |
| **Factor** | skip path: plain concatenation **vs** additive attention gate |
| **Levels** | `unet` · `attention_unet` |
| **Status** | **EXECUTED as the M11 main experiment** — see [`04_RESULTS.md`](04_RESULTS.md). Result: thin cloud +0.050 (3/3), cloud shadow −0.018 (3/3), overall **MIXED**. |

*This is the one row in this document that is not empty, and it is the M11 experiment itself rather than
an additional ablation.*

## A2 — Attention gate placement (per-stage)

| Field | Value |
|---|---|
| **Question** | Do all decoder stages contribute, or is the gain driven by one resolution level? |
| **Hypothesis** | Thin cloud is low-contrast and spatially diffuse, so **higher-resolution** (shallower) gates may matter most. |
| **Factor** | gates enabled at stage {1}, {2}, {3}, {1,2}, {1,2,3} |
| **Fixed** | everything in the common protocol |
| **Metric** | thin-cloud IoU; parameter count per variant |
| **Implementation** | requires a per-stage gate flag in `attention_unet` — **not currently implemented** |
| **Result** | **NOT EXECUTED** |

## A3 — Loss configuration

| Field | Value |
|---|---|
| **Question** | Does an imbalance-aware loss change the thin-cloud/cloud-shadow trade-off? |
| **Hypothesis** | Plain cross-entropy under-weights the rare classes; Dice / generalised Dice may lift thin cloud **and** cloud shadow together, changing the MIXED verdict. |
| **Factor** | cross-entropy (M11 baseline) · Dice · CE + Dice · generalised Dice |
| **Prior art** | [Milletari et al. 2016](references.bib); [Sudre et al. 2017](references.bib) |
| **Fixed** | architecture pair, data, schedule |
| **Metric** | thin-cloud IoU **and** cloud-shadow IoU (both — this ablation is about the trade-off) |
| **Implementation** | `app/training/loss.py` already supports configurable loss — **no new code needed** |
| **Result** | **NOT EXECUTED** |

## A4 — Class weighting

| Field | Value |
|---|---|
| **Question** | Is the cloud-shadow regression caused by class imbalance rather than by attention? |
| **Hypothesis** | Cloud shadow is 11.1% of pixels; up-weighting it may remove the regression. If it does, the MIXED verdict is a *weighting* artifact, not an architectural one — **this is the ablation most likely to change the paper's conclusion**. |
| **Factor** | uniform · inverse-frequency · manual shadow up-weighting |
| **Metric** | cloud-shadow IoU (primary here); thin-cloud IoU must not regress |
| **Result** | **NOT EXECUTED** |

## A5 — Seed count / stability

| Field | Value |
|---|---|
| **Question** | Is the seed-dependent overall verdict (IMPROVED / REGRESSION / REGRESSION) a small-n artifact? |
| **Hypothesis** | At n=3 the framework verdict is unstable; more seeds would show whether it converges. |
| **Factor** | n ∈ {3 (done), 5, 10} |
| **Metric** | per-seed verdict distribution; spread of thin-cloud ΔIoU |
| **Note** | Only at sufficient n does a **significance test** become meaningful. At n=3 none is reported (ADR-0011). |
| **Result** | **NOT EXECUTED** for n > 3 |

## A6 — Subset size

| Field | Value |
|---|---|
| **Question** | Does the thin-cloud gain persist as data grows, or is it a small-data effect? |
| **Hypothesis** | Attention gates help most when data is scarce; the gain may shrink with more samples. |
| **Factor** | 32 (done) · 64 · 128 · 256 expert-labelled samples |
| **Note** | Requires re-running the M12 acquisition + readiness gate at each size; storage budget applies (Risk R-03). |
| **Result** | **NOT EXECUTED** for n > 32 |

## A7 — Training duration

| Field | Value |
|---|---|
| **Question** | Are both arms converged at 12 epochs, or does the comparison measure convergence speed? |
| **Hypothesis** | If the baseline is under-trained at 12 epochs, part of the "gain" is faster convergence, not better final quality. **This is a validity threat to the M11 result**, not merely a tuning question. |
| **Factor** | epochs ∈ {12 (done), 25, 50} with early stopping on val thin-cloud IoU |
| **Metric** | thin-cloud IoU at convergence; epochs-to-best per arm |
| **Result** | **NOT EXECUTED** |

## A8 — Patch size

| Field | Value |
|---|---|
| **Question** | Does more spatial context help cloud shadow (a geometrically-defined class)? |
| **Hypothesis** | Shadow position depends on cloud geometry and illumination; 128 px may not contain the casting cloud. CloudSEN12+ explicitly added a 2000×2000 option citing better shadow context. |
| **Factor** | 128 (done) · 256 · 512 |
| **Constraint** | MPS memory (ADR-0002); larger patches may force a smaller batch, which breaks the fixed-batch control — batch would become a confound to be reported. |
| **Result** | **NOT EXECUTED** |

---

## Priority if resources become available

| Rank | Ablation | Why first |
|---|---|---|
| 1 | **A4 class weighting** | Directly tests whether the cloud-shadow regression — the thing that makes the verdict MIXED — is an imbalance artifact rather than an architectural cost. Highest chance of changing the conclusion. |
| 2 | **A7 training duration** | A validity threat to the existing result; cheap to run. |
| 3 | **A5 seed count** | Needed before any significance claim is legitimate. |
| 4 | **A6 subset size** | Establishes whether the finding survives scale. |
| 5 | **A3 loss** | Natural follow-on to A4. |
| 6 | **A8 patch size** | Targets cloud shadow specifically; costlier. |
| 7 | **A2 gate placement** | Mechanistic insight; needs new code. |

**None of the above has been run.** Any future execution must update this document with per-seed values
and its own status labels, and must not overwrite the M11 result.
