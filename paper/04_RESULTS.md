# Results

**Milestone 19 · Deliverable D7.** Evidence policy: [ADR-0019](../docs/adr/ADR-0019-research-paper-and-evidence-policy.md).

> **Provenance rule.** Every number on this page is **transcribed** from
> [`docs/comparison/real_experiment_cloudsen12.md`](../docs/comparison/real_experiment_cloudsen12.md),
> the M11 measured-run record. Nothing is recomputed, re-weighted, or re-interpreted here (ADR-0019 §3).
> The only quantities derived on this page are the arithmetic summaries the source itself already
> states (means over the three seeds), and they are marked as such.

**Status of everything below: `REAL — BOUNDED M11 EXPERIMENT`** unless explicitly labelled otherwise.

---

## 1. What was run

A single controlled comparison — U-Net (baseline) vs Attention U-Net (improved) — on real
expert-labelled CloudSEN12+ Sentinel-2 data, executed on Apple MPS.

| Property | Value |
|---|---|
| Source | `tacofoundation/cloudsen12`, variant `cloudsen12-l1c`, via tacoreader 0.6.5 |
| Licence | **CC0-1.0** (public domain) |
| `dataset_version` | `cloudsen12plus-1.1.2-l1c-p0-9045d5c3` |
| Subset | **32** samples, `label_type=high` (expert-labelled), L1C part 0, deterministic selection (seed 1) |
| Imagery / labels | 13-band uint16 512×512 (nodata 65535); uint8 512×512 labels, **0=clear, 1=thick, 2=thin, 3=cloud_shadow** |
| Split (ROI-grouped, class-stratified) | **train 22 / val 5 / test 5**; `leakage_ok = True`; 512 patches @ 128 px |
| Normalization | min–max, **fit on train only**, applied identically to val/test |
| Readiness gate | `is_experiment_ready() == TRUE` |
| Device | **MPS** (CUDA = False), recorded per artifact |
| Seeds | **3** |

**Class distribution (pixels).** Overall: clear **40.1%**, thick **32.1%**, thin **16.7%**, shadow
**11.1%**. Thin cloud is present in **every** split (test split: 26.5% thin, 12.4% shadow). This matters:
without class-stratified splitting the 5-sample test split contained *no* thin cloud at all and the
primary metric was undefined — the run would have been INCONCLUSIVE for a purely procedural reason.

## 2. Fairness controls

Both arms shared **identical** dataset, split, preprocessing, normalization, seed, patch size (128),
batch size (8), epochs (12), optimizer (AdamW), scheduler (cosine), loss (cross-entropy), checkpoint
policy, and device. **Only the architecture differed.**

| Model | Parameters | Ratio |
|---|---:|---:|
| U-Net (baseline) | **484,228** | 1.000 |
| Attention U-Net (improved) | **490,005** | **×1.012** |

Attention training time ≈ **×1.2–1.3** baseline. *(Parameter counts independently re-derived from the
model code at the run configuration `encoder_depth=3, base_channels=16, in_channels=13, num_classes=4`
during M19 verification; both matched the recorded values exactly.)*

## 3. Per-class IoU delta, all three seeds

ΔIoU = improved − baseline. Positive favours Attention U-Net.

| Class | Seed 1 | Seed 2 | Seed 3 | Mean (derived) | Direction |
|---|:---:|:---:|:---:|:---:|---|
| clear | −0.024 | −0.014 | +0.039 | +0.000 | inconsistent |
| thick_cloud | −0.057 | +0.028 | +0.122 | +0.031 | inconsistent |
| **thin_cloud (PRIMARY)** | **+0.047** | **+0.076** | **+0.028** | **+0.050** | **improves in 3/3** |
| cloud_shadow | −0.003 | −0.029 | −0.022 | −0.018 | **regresses in 3/3** |
| macro IoU | −0.009 | +0.015 | +0.042 | +0.016 | inconsistent |

Two classes are **consistent** across seeds, in opposite directions: thin cloud always improves, cloud
shadow always regresses. Clear, thick and macro IoU **change sign** between seeds and therefore support
no directional claim at n=3.

## 4. Thin cloud — the primary research target

| Seed | IoU base → impr (Δ) | Dice Δ | Recall base → impr | False negatives base → impr |
|---|---|---|---|---|
| 1 | 0.4605 → 0.5073 (**+0.047**) | +0.043 | 0.666 → 0.745 | 115,948 → 88,554 |
| 2 | 0.4402 → 0.5158 (**+0.076**) | +0.069 | 0.556 → 0.705 | 154,221 → 102,652 |
| 3 | 0.5244 → 0.5520 (**+0.028**) | +0.023 | 0.736 → 0.847 | 91,693 → 53,215 |

**Thin-cloud IoU improves in all 3 seeds: mean +0.050 (± 0.020).** Recall improves in every seed
(+0.079, +0.149, +0.111) and false negatives fall in every seed (−27,394; −51,569; −38,478).

**INTERPRETATION:** the recall and false-negative movement indicates the gain comes from *recovering
thin cloud the baseline misses*, rather than from trading precision elsewhere — consistent with the
ADR-0010 hypothesis that attention gates help the model attend to low-contrast, sparsely distributed
evidence. This is our reading of the measured direction, not an additional measurement.

## 5. Cloud shadow — the hardest class

ΔIoU = **[−0.003, −0.029, −0.022]**; mean **−0.018**. Baseline cloud-shadow IoU is **≈0.08–0.10** for
*both* models on this subset.

Two facts must be held together:
- The regression is **consistent** (3/3 seeds) and is what makes the overall verdict MIXED.
- Both models are **weak in absolute terms** on this class (IoU ≈ 0.1), so this is a small change on a
  low base, not the degradation of a working capability.

**INTERPRETATION:** cloud shadow is under-represented (11.1% of pixels) and geometrically rather than
purely radiometrically defined; a skip-reweighting mechanism tuned by the dominant classes may
de-emphasise it. **Untested** — this is a candidate explanation and a motivation for the class-weighting
ablation, not a finding.

## 6. Failure analysis (M9, on real test predictions)

Run per seed on real predictions. Thin-cloud failures (false-negative pixels) **fall every seed** — e.g.
seed 1: 115,948 → 88,554.

| Failure category | Status |
|---|---|
| Thin-cloud false negatives | **MEASURED** (above) |
| Confidence-based categories | **NOT MEASURABLE** — predicted probabilities were not persisted |
| Edge / small-object categories | **DEFERRED** — no spatial connected-component analysis implemented |

## 7. The decision — MIXED

The M11 decision framework ([ADR-0011](../docs/adr/ADR-0011-model-comparison.md)) returns a verdict per
seed. **The verdict flips across seeds:**

| Seed | Framework verdict |
|---|---|
| 1 | **IMPROVED** |
| 2 | **REGRESSION** |
| 3 | **REGRESSION** |

Seeds 2 and 3 return REGRESSION because the framework penalises worst-class regression — the
cloud-shadow drop — by design. That guardrail exists precisely so that a favourable headline metric
cannot conceal a class that got worse.

> ### Overall conclusion: **MIXED**
>
> On this bounded subset, Attention U-Net is **not a uniform winner**. It trades cloud-shadow and
> thick-cloud stability for a reliable thin-cloud gain. With only 3 seeds, no formal significance test,
> and a seed-dependent overall verdict, we do **not** declare Attention U-Net superior overall. We
> **do** report a measured, consistent thin-cloud improvement.

**This conclusion is transcribed verbatim in substance from the M11 record and must not be restated as
"Attention U-Net is better."** That claim is not supported by this evidence.

## 8. What these numbers are *not*

| | |
|---|---|
| **Not** the AC-4 frozen-envelope benchmark | 32 samples, one small config, 12 epochs, 3 seeds |
| **Not** project KPI values | KPI-1..6 and KPI-E1..E7 remain **NOT YET MEASURED** |
| **Not** statistically tested | n=3, no significance test; spread is descriptive (± population SD) |
| **Not** cross-region or cross-season | AC-1 evidence: **NOT YET MEASURED** |
| **Not** compared to published methods | No Fmask / GCDB-UNet / leaderboard comparison: **NOT EXECUTED** |
| **Not** generalisable beyond this subset | One L1C part, one configuration |

## 9. Evidence status summary

| Class | Item |
|---|---|
| **REAL — BOUNDED M11 EXPERIMENT** | Everything in §1–§7 |
| **SYNTHETIC** | All API `/train` `/predict` `/evaluate` output; M11/M12 pipeline-validation runs. Never promoted. |
| **DEMO** | Degraded mode, recovery, lineage (M15) |
| **PLANNED / NOT EXECUTED** | All ablations ([`03_ABLATION_TEMPLATE.md`](03_ABLATION_TEMPLATE.md)); published-baseline comparison |
| **DEFERRED** | Spatial/edge failure categories; confidence calibration |
| **NOT MEASURABLE** | Confidence-based failure categories (probabilities not persisted) |
| **NOT YET MEASURED** | KPI-1..6, KPI-E1..E7; AC-1, AC-3, AC-4 |
| **NOT BUILT** | FR-2 `run_reference.sh`; `evaluation/oracle.py` → independent reference validation **NOT EXECUTABLE** |

## 10. Reproducibility of this run

Recorded deterministic hashes: `config_hash`, dataset `content_hash`, `subset_selection_hash`,
`split_config_hash`, `normalization_hash` in `data/processed/cloudsen12/dataset_artifact.json`. Per-seed
comparison artifacts under `data/processed/cloudsen12/m11*/comparison_artifact.json` (git-ignored — raw
data and artifacts are never committed). The bounded subset is reproducible from `(seed=1,
subset_size=32)` against L1C part 0.

**Caveat:** re-running reproduces the *subset and configuration* deterministically. Exact metric
reproduction additionally depends on device and library versions; the device is recorded in every
artifact so results are never compared across envelopes by accident.
