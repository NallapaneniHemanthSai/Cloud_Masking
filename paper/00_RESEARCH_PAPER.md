# Attention-Gated Skip Connections for Thin-Cloud Segmentation in Sentinel-2: A Bounded Controlled Comparison

**Draft — Milestone 19 · Deliverable D7.**
Evidence policy: [ADR-0019](../docs/adr/ADR-0019-research-paper-and-evidence-policy.md).
Supporting documents: [literature review](01_LITERATURE_REVIEW.md) · [comparison table](02_COMPARISON_TABLE.md)
· [ablation template](03_ABLATION_TEMPLATE.md) · [results](04_RESULTS.md) · [references](references.bib).

> **How to read this paper.** Every substantive claim is one of three kinds, and the kind is marked:
> **SOURCE-DERIVED FACT** (from a cited publication), **PROJECT RESULT** (measured by us, with a status
> label), or **INTERPRETATION** (our reading). Unmeasured quantities are written as their status —
> `NOT YET MEASURED`, `NOT EXECUTED`, `DEFERRED`, `NOT BUILT` — never as a number.
>
> **The headline result is MIXED, not a win.** Attention U-Net improved thin cloud consistently and
> regressed cloud shadow consistently. Any summary of this work that says "Attention U-Net is better"
> misrepresents it.

---

## Abstract

Optical satellite imagery is unusable where cloud is undetected, and the hardest cases are the
semi-transparent ones: thin cloud, haze, and cloud shadow over bright surfaces. We ask a narrow,
testable question: **do additive attention gates on U-Net's skip connections improve thin-cloud
segmentation in 13-band Sentinel-2 imagery?** The mechanism is established for medical imaging
[oktay2018attentionunet] but not for multispectral remote sensing, where the targets are radiometrically
rather than anatomically defined.

We ran one controlled comparison of U-Net against Attention U-Net on a bounded 32-sample
expert-labelled CloudSEN12+ subset [aybar2024cloudsen12plus], three seeds, with every factor except the
skip path held identical. **Thin-cloud IoU improved in all three seeds (mean +0.050), with recall up and
false negatives down in every seed, at ×1.012 parameters and ×1.2–1.3 training time. Cloud-shadow IoU
regressed in all three seeds (mean −0.018).** Our decision framework, which penalises worst-class
regression by design, returned IMPROVED for one seed and REGRESSION for two.

**We therefore report a MIXED result and do not claim the improved architecture is superior.** This is a
bounded first experiment — not a frozen-envelope benchmark — and all formal project KPIs remain
**NOT YET MEASURED**. The contribution is a fully specified, fairness-guarded, honestly-reported
comparison, including the class that got worse.

---

## 1. Problem statement

Cloud contamination is the dominant data-loss mechanism in optical Earth observation. A cloud mask
decides which pixels enter any downstream analysis, so masking errors propagate: a missed thin cloud
silently corrupts a surface measurement, while an over-aggressive mask discards valid data.

The failure is not uniform across cloud types. Thick, bright, opaque cloud is comparatively easy —
strong spectral contrast against most surfaces. The difficulty concentrates in:

- **thin / semi-transparent cloud**, where surface and cloud signal mix in one pixel;
- **cloud shadow**, defined by illumination geometry as much as by spectral response;
- **bright surfaces** (snow, ice, sand, salt, rooftops) that mimic cloud spectrally.

This project targets that hard core: **thin cloud, haze, snow and bright surfaces**.

## 2. Motivation

The motivation is quantitative and comes from the dataset authors themselves.

**SOURCE-DERIVED FACT** [aybar2022cloudsen12]: expert human annotators reached **95.7% overall**
agreement but only **78% producer's accuracy on thin cloud**, which "were always the source of the most
contention." Cloud shadow drew **21% disagreement** among expert reviewers, partly because thin
low-altitude clouds cast shadows on the surface.

**INTERPRETATION:** two things follow. First, thin cloud is genuinely hard, not merely
under-engineered — it is the class where trained experts disagree most. Second, thin-cloud label noise
places a ceiling on achievable performance, so thin-cloud IoU cannot be read on the same scale as
clear-class IoU. This is our reasoning; the source reports the agreement figures, not this implication.

A second motivation is methodological. Aggregate accuracy is dominated by easy pixels. In our subset
clear and thick cloud are **72.2%** of pixels while thin cloud is **16.7%** — a model can post strong
overall accuracy while failing the class the work is about. This project treats that as a **guardrail
condition** (NT-1), not a reporting preference: a run that passes on average but fails a critical
subgroup is a **fail**.

## 3. Dataset and task

**SOURCE-DERIVED FACT** [aybar2022cloudsen12; aybar2024cloudsen12plus]: CloudSEN12 provides 49,400
Sentinel-2 patches over 9,880 ROIs with tiered annotation (high-quality pixel-level, scribble,
no-annotation). CloudSEN12+ more than doubles the expert-labelled annotations, exceeds 50,000 patches,
adds a 2000×2000 patch option for better shadow context, corrects 452 mislabelled images, and is
released under **CC0**.

We use **CloudSEN12+**, L1C, expert-labelled tier. The CC0 licence is the reason derived artifacts are
redistributable here, unlike the competition-licensed *On Cloud N* corpus, which this project retains as
a reference benchmark only and never redistributes.

### 4. Four-class cloud segmentation

Per-pixel classification into four mutually exclusive classes (dataset encoding):

| Code | Class | Why it is hard |
|:---:|---|---|
| 0 | **clear** | Majority class; bright surfaces (snow, sand, rooftops) mimic cloud spectrally |
| 1 | **thick_cloud** | Comparatively easy — high reflectance, strong contrast |
| 2 | **thin_cloud** | **Primary target.** Mixed surface/cloud signal in one pixel; ~78% expert agreement |
| 3 | **cloud_shadow** | Geometric as well as spectral; confusable with water and terrain shadow |

**Haze** has no separate label in CloudSEN12 and is **approximated within the thin-cloud class**,
reported qualitatively inside that stratum. It has **no standalone KPI** — a scope decision recorded
before any experiment, not a post-hoc convenience.

Input is **13-band uint16, 512×512** at 10 m; labels are uint8 512×512.

## 5. Baseline: U-Net

**SOURCE-DERIVED FACT** [ronneberger2015unet]: U-Net pairs a contracting encoder with a symmetric
expanding decoder, joined by skip connections that **concatenate** encoder features into the decoder,
and trains end-to-end from few annotated images with heavy augmentation.

We adopt it as the baseline ([ADR-0006](../docs/adr/ADR-0006-baseline-model-selection.md)) for its
strong precedent, low parameter count, and clean fit to the Apple-Silicon (MPS) envelope this project is
constrained to — no CUDA is available.

**The specific limitation we target:** skips are fused **unweighted**. Every encoder location
contributes equally regardless of relevance. **INTERPRETATION:** for a low-contrast, spatially diffuse
class such as thin cloud, unfiltered skip features may dilute the weak evidence that distinguishes it.

## 6. Improved model: Attention U-Net

**SOURCE-DERIVED FACT** [oktay2018attentionunet]: attention gates inserted into skip connections learn
to "suppress irrelevant regions in an input image while highlighting salient features," removing the
need for a cascaded localisation module while remaining computationally cheap. The authors report AGs
"consistently improve the prediction performance of U-Net across different datasets and training sizes"
— **on two abdominal CT datasets**.

We adopt additive attention gates ([ADR-0010](../docs/adr/ADR-0010-improved-model-selection.md)): three
1×1 convolutions per decoder stage (`W_g`, `W_x`, `ψ`) re-weight encoder features, conditioned on the
decoder signal, before concatenation. The encoder, decoder, and all shared blocks are **unchanged**.

**Critically, the source evidence does not transfer automatically.** It is single-modality anatomical CT
with anatomically-constrained targets; ours is 13-band multispectral satellite imagery with
semi-transparent targets and radiometric boundaries. We therefore treat the benefit as a hypothesis to
be tested, not an inherited result.

Independent corroboration of the *direction*: **SOURCE-DERIVED FACT** [li2022gcdbunet] — GCDB-UNet also
identifies thin cloud as plain U-Net's failure mode and also reaches for attention (non-local
self-attention + squeeze-excitation), motivated by thin clouds' "small sizes and sparse distributions."
Different formulation, different data — supportive of the direction, **not** evidence for our result.

### 7. Hypothesis (pre-registered)

Stated in ADR-0010 **before** any comparison was run:

> *The baseline U-Net may be limited in how selectively it aggregates skip-connection features. Adding
> attention gates that re-weight skip features by relevance should improve difficult cloud classes
> (especially thin cloud) and boundary failure cases, without imposing unreasonable compute cost.*

Three testable parts: (a) thin cloud improves; (b) boundary/failure cases improve; (c) compute cost stays
reasonable. **Part (b) was never tested** — spatial connected-component failure analysis is DEFERRED.
That is a gap in the test of the hypothesis, not a silent omission.

## 8. Training methodology

One trainer serves both arms ([ADR-0007](../docs/adr/ADR-0007-training-strategy.md)) — there is no
second training engine, so no arm can be advantaged by its harness.

| Element | Value |
|---|---|
| Optimizer / scheduler | AdamW / cosine |
| Loss | cross-entropy (identical both arms) |
| Patch / batch | 128 px / 8 |
| Epochs | 12 |
| Seeds | 3, deterministic seeding |
| Device | MPS (recorded per run; CUDA unavailable) |
| Normalization | min–max, **fit on train only** |

**Fairness controls (M11):** identical dataset, split, preprocessing, normalization, seed, patch size,
batch size, epochs, optimizer, scheduler, loss, checkpoint policy and device. **Only the architecture
differs.** Both arms even receive identical fixed-order batches.

## 9. Evaluation methodology

Confusion-matrix-first ([ADR-0008](../docs/adr/ADR-0008-evaluation-strategy.md)). Per-class IoU, Dice,
precision, recall, F1 are derived from one confusion matrix per run; macro and weighted aggregates are
computed but are never the basis of a success claim.

Three rules that shape what this paper can say:

1. **Undefined is reported as undefined.** A class absent from a split yields no metric; it is never
   substituted with 0.
2. **Thin cloud is the primary metric.** Chosen before results existed.
3. **Aggregates may not hide subgroups.** A stronger macro score that conceals thin-cloud degradation is
   classified as a **REGRESSION**, not an improvement.

**Split integrity:** ROI-grouped, class-stratified, with an automated leakage check (`leakage_ok`).
Whole ROIs never span splits. Normalization statistics come from train only.

## 10. Failure-analysis methodology

M9 ([ADR-0009](../docs/adr/ADR-0009-confusing-case-analysis.md)) provides a taxonomy with an explicit
**measurability** status per category — the mechanism that prevents reporting a category we cannot
actually compute:

| Category | Status in this work |
|---|---|
| Per-class false negatives / positives | **MEASURED** |
| Confidence-based (low-confidence errors) | **NOT MEASURABLE** — predicted probabilities were not persisted |
| Edge / boundary / small-object | **DEFERRED** — no connected-component analysis implemented |

## 11. Controlled comparison (M11)

The comparison framework ([ADR-0011](../docs/adr/ADR-0011-model-comparison.md)) reuses the M7 trainer,
M8 evaluation and M9 failure analysis — it adds no metric of its own. It returns one of
**IMPROVED / NO_SIGNIFICANT_IMPROVEMENT / REGRESSION / INCONCLUSIVE / COMPUTE_UNJUSTIFIED**, in priority
order over thin-cloud IoU/Dice, macro performance, worst-class behaviour, failure behaviour, compute
cost and seed count, with these rules fixed in advance:

- an aggregate gain that **hides thin-cloud degradation is a REGRESSION**;
- a slight gain at large compute cost is **COMPUTE_UNJUSTIFIED**;
- synthetic or absent results yield **INCONCLUSIVE** — never a guessed winner;
- fewer than two seeds ⇒ significance **NOT_MEASURED**.

## 12. Results

Full detail and provenance: [`04_RESULTS.md`](04_RESULTS.md). **Status: REAL — BOUNDED M11 EXPERIMENT.**

**Setup.** 32 expert-labelled CloudSEN12+ L1C samples (`cloudsen12plus-1.1.2-l1c-p0-9045d5c3`, CC0);
ROI-grouped stratified split train 22 / val 5 / test 5, `leakage_ok = True`; 512 patches @ 128 px; class
distribution clear 40.1% / thick 32.1% / **thin 16.7%** / shadow 11.1%; readiness gate TRUE.

**Cost.** U-Net **484,228** parameters; Attention U-Net **490,005** (**×1.012**); training time
**×1.2–1.3**.

**Per-class ΔIoU (improved − baseline):**

| Class | Seed 1 | Seed 2 | Seed 3 | Mean | Consistent? |
|---|:---:|:---:|:---:|:---:|:---:|
| clear | −0.024 | −0.014 | +0.039 | +0.000 | no |
| thick_cloud | −0.057 | +0.028 | +0.122 | +0.031 | no |
| **thin_cloud** | **+0.047** | **+0.076** | **+0.028** | **+0.050** | **3/3 ↑** |
| cloud_shadow | −0.003 | −0.029 | −0.022 | −0.018 | **3/3 ↓** |
| macro IoU | −0.009 | +0.015 | +0.042 | +0.016 | no |

**Framework verdict:** seed 1 **IMPROVED**, seeds 2 and 3 **REGRESSION** → overall **MIXED**.

### 13. Thin-cloud analysis

| Seed | IoU base → impr | Δ | Recall base → impr | False negatives |
|---|---|:---:|---|---|
| 1 | 0.4605 → 0.5073 | +0.047 | 0.666 → 0.745 | 115,948 → 88,554 |
| 2 | 0.4402 → 0.5158 | +0.076 | 0.556 → 0.705 | 154,221 → 102,652 |
| 3 | 0.5244 → 0.5520 | +0.028 | 0.736 → 0.847 | 91,693 → 53,215 |

Mean ΔIoU **+0.050 (± 0.020**, population SD over 3 seeds — descriptive spread, **not** a confidence
interval**)**. IoU, Dice, recall and false negatives all move favourably in **every** seed.

**INTERPRETATION:** recall rising while false negatives fall indicates the gain comes from **recovering
thin cloud the baseline misses**, not from a precision/recall trade elsewhere. That is the behaviour the
attention-gate hypothesis predicts. It remains an interpretation of direction, not an additional
measurement, and it holds only on this subset.

### 14. Cloud-shadow analysis

ΔIoU **[−0.003, −0.029, −0.022]**, mean **−0.018** — a regression in **3/3** seeds. Baseline
cloud-shadow IoU is **≈0.08–0.10** for *both* models.

Both facts matter. The regression is **consistent**, which is why the verdict is MIXED and why we do not
claim superiority. But both models are **weak in absolute terms** on this class, so this is a small
decrement on a low base, not the loss of a working capability.

**INTERPRETATION (untested):** cloud shadow is the rarest class (11.1%) and is defined by illumination
geometry; a skip-reweighting mechanism whose signal is dominated by the majority classes may
de-emphasise it. This motivates ablations **A4 (class weighting)** and **A8 (patch size)** — neither has
been run.

### 15. Failure cases

Thin-cloud false-negative pixels fall in every seed (seed 1: 115,948 → 88,554; seed 2: 154,221 → 102,652;
seed 3: 91,693 → 53,215) — the improvement is visible in the failure counts, not only in the aggregate
metric. Confidence-based categories are **NOT MEASURABLE** (probabilities not persisted); edge and
small-object categories are **DEFERRED**. The boundary half of the ADR-0010 hypothesis is therefore
**untested**.

## 16. Limitations

Stated plainly, because they bound every claim above.

1. **Bounded subset.** 32 samples, one L1C part, one small configuration, 12 epochs. **Not** the AC-4
   frozen-envelope benchmark.
2. **n = 3 seeds, no significance test.** Consistency (3/3) is reportable; statistical significance is
   **NOT MEASURED**. No confidence intervals are given.
3. **Seed-dependent overall verdict** (IMPROVED / REGRESSION / REGRESSION) — the aggregate conclusion is
   not stable at this n.
4. **Cloud-shadow IoU ≈ 0.1 for both models** — a hard, under-represented class on this subset.
5. **Convergence unverified.** Whether 12 epochs converges both arms is untested (ablation A7); part of
   the measured difference could be convergence speed rather than final quality. **A genuine validity
   threat**, not a tuning detail.
6. **No comparison to published methods.** No Fmask, GCDB-UNet, or leaderboard comparison was run.
7. **No cross-region or cross-season evaluation.** AC-1 evidence is **NOT YET MEASURED**.
8. **Boundary hypothesis untested** (spatial failure analysis DEFERRED).
9. **Formal KPIs unmeasured.** KPI-1..6 and KPI-E1..E7 remain **NOT YET MEASURED**; the project's Pass
   Contract is not yet satisfiable.
10. **Label noise.** ~78% expert agreement on thin cloud [aybar2022cloudsen12] bounds achievable
    performance and is not corrected for.

## 17. Reproducibility

**What is reproducible.** Deterministic `config_hash`, dataset `content_hash`, `subset_selection_hash`,
`split_config_hash`, `normalization_hash`; the subset regenerates from `(seed=1, subset_size=32)` against
L1C part 0; dependencies are exactly pinned and the container asserts its own imports at build time; the
whole system runs from `docker compose up`; the acceptance harness produces a byte-identical content hash
on host and in-container.

**What is not.** Exact metric values depend on device and library versions (the device is recorded in
every artifact so envelopes are never mixed). Raw data and run artifacts are git-ignored and never
committed.

**An explicit gap — FR-2, and it is an O5 blocker:**

| Component | Status |
|---|---|
| `scripts/run_reference.sh` (one-command reference path) | **NOT BUILT** |
| `backend/evaluation/oracle.py` (independent expected-result oracle) | **NOT BUILT** |
| Independent reference validation | **NOT EXECUTABLE** |

FR-2 requires that a one-command run rebuild the baseline and that an **independent oracle** re-derive
the expected metrics. Neither component exists. Consequently the results in §12–§15 are reproducible
*by re-running our own pipeline*, but have **not** been independently re-derived. This is recorded, not
worked around; closing it belongs to the M6–M9 workstream and is a prerequisite for independent
acceptance (O5).

## 18. Future work

In priority order, with the reasoning that sets the order:

1. **Ablation A4 (class weighting)** — tests whether the cloud-shadow regression is an imbalance
   artifact rather than an architectural cost. **Most likely single result to change this paper's
   MIXED conclusion.**
2. **Ablation A7 (training duration)** — closes validity threat (5).
3. **FR-2 reference path + independent oracle** — unblocks O5.
4. **Ablation A5 (more seeds)** — the precondition for any legitimate significance claim.
5. **AC-4 frozen-envelope evaluation on the full dataset** — the only route to moving KPI-1..6 off
   **NOT YET MEASURED**.
6. **Cross-region / cross-season stratification** — AC-1 evidence.
7. **Comparison against published baselines** (Fmask 4.0, GCDB-UNet).
8. **Spatial failure analysis** — tests the untested boundary half of the hypothesis.
9. **Downstream change-detection impact** (KPI-3), with OSCD [daudt2018oscd] as the candidate source.

## 19. Conclusion

We asked whether additive attention gates on U-Net's skip connections improve thin-cloud segmentation in
Sentinel-2 imagery, and we answered it with one controlled, fairness-guarded, three-seed experiment on
real expert-labelled CloudSEN12+ data.

**The measured answer is partial and we report it as such.** Thin-cloud IoU improved in all three seeds
(mean **+0.050**), with recall up and false negatives down every time, at a negligible **×1.012**
parameter cost — real evidence for the pre-registered hypothesis on its primary target. Cloud-shadow IoU
regressed in all three seeds (mean **−0.018**), and our decision framework, which is built to refuse
improvements that hide a worse class, returned REGRESSION for two of three seeds.

**The overall verdict is MIXED. Attention U-Net is not a uniform winner on this evidence, and we do not
claim it is better.** What we claim is narrower and better supported: on this bounded subset, attention
gates deliver a **consistent, mechanism-plausible thin-cloud gain** at negligible parameter cost, with a
**consistent small cost to the hardest class**.

The wider position is equally explicit. All formal KPIs remain **NOT YET MEASURED**; every ablation is
**NOT EXECUTED**; the FR-2 independent reference path is **NOT BUILT**; and the project's Pass Contract
is not yet satisfiable. Reporting a clean victory here would have required either ignoring the
cloud-shadow regression or filling empty tables with plausible numbers. The contribution of this work is
that it does neither.

---

## References

Full BibTeX: [`references.bib`](references.bib). Every entry verified against Crossref or the arXiv API.

1. **[aybar2022cloudsen12]** Aybar, C. et al. *CloudSEN12, a global dataset for semantic understanding of cloud and cloud shadow in Sentinel-2.* Scientific Data **9**, 782 (2022). doi:10.1038/s41597-022-01878-2
2. **[aybar2024cloudsen12plus]** Aybar, C. et al. *CloudSEN12+: The largest dataset of expert-labeled pixels for cloud and cloud shadow detection in Sentinel-2.* Data in Brief **56**, 110852 (2024). doi:10.1016/j.dib.2024.110852
3. **[ronneberger2015unet]** Ronneberger, O., Fischer, P. & Brox, T. *U-Net: Convolutional Networks for Biomedical Image Segmentation.* MICCAI 2015, LNCS, 234–241. doi:10.1007/978-3-319-24574-4_28
4. **[oktay2018attentionunet]** Oktay, O. et al. *Attention U-Net: Learning Where to Look for the Pancreas.* MIDL 2018. arXiv:1804.03999
5. **[zhu2012fmask]** Zhu, Z. & Woodcock, C. E. *Object-based cloud and cloud shadow detection in Landsat imagery.* Remote Sensing of Environment **118**, 83–94 (2012). doi:10.1016/j.rse.2011.10.028
6. **[qiu2019fmask4]** Qiu, S., Zhu, Z. & He, B. *Fmask 4.0: Improved cloud and cloud shadow detection in Landsats 4–8 and Sentinel-2 imagery.* Remote Sensing of Environment **231**, 111205 (2019). doi:10.1016/j.rse.2019.05.024
7. **[tarrio2020comparison]** Tarrio, K. et al. *Comparison of cloud detection algorithms for Sentinel-2 imagery.* Science of Remote Sensing **2**, 100010 (2020). doi:10.1016/j.srs.2020.100010
8. **[li2022gcdbunet]** Li, X. et al. *GCDB-UNet: A novel robust cloud detection approach for remote sensing images.* Knowledge-Based Systems **238**, 107890 (2022). doi:10.1016/j.knosys.2021.107890
9. **[milletari2016vnet]** Milletari, F., Navab, N. & Ahmadi, S.-A. *V-Net: Fully Convolutional Neural Networks for Volumetric Medical Image Segmentation.* 3DV 2016, 565–571. doi:10.1109/3DV.2016.79
10. **[sudre2017generalised]** Sudre, C. H. et al. *Generalised Dice Overlap as a Deep Learning Loss Function for Highly Unbalanced Segmentations.* DLMIA 2017, LNCS, 240–248. doi:10.1007/978-3-319-67558-9_28
11. **[daudt2018oscd]** Caye Daudt, R., Le Saux, B., Boulch, A. & Gousseau, Y. *Urban Change Detection for Multispectral Earth Observation Using Convolutional Neural Networks.* IGARSS 2018, 2115–2118. doi:10.1109/IGARSS.2018.8518015
