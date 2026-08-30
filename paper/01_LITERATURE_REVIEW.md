# Literature Review

**Milestone 19 · Deliverable D7.** Decisions: [ADR-0019](../docs/adr/ADR-0019-research-paper-and-evidence-policy.md).
BibTeX: [`references.bib`](references.bib).

> **Evidence discipline.** Everything in the *Source-derived fact* columns below is what the cited work
> itself reports. Nothing here is a result of this project — for those, see
> [`04_RESULTS.md`](04_RESULTS.md). Where we draw our own inference from a source it is marked
> **INTERPRETATION**.

## Verification method

Citation metadata is a common silent-error source, so no entry was written from memory. Each was
verified against a primary metadata service:

| Source of truth | Used for | Result |
|---|---|---|
| Crossref REST API (`api.crossref.org/works/<DOI>`) | 10 published works | all 10 resolved; title/authors/venue/volume/pages/year taken from the response |
| arXiv API (`export.arxiv.org/api/query`) | 2 preprints of record | both resolved; MIDL'18 / MICCAI'15 acceptance confirmed from the arXiv comment field |

Selection rule (ADR-0019): peer-reviewed publications, official dataset papers, or archival preprints
only. Blogs, vendor documentation, and secondary summaries were excluded as scientific evidence.

---

## 1. The dataset and task

### CloudSEN12 — Aybar et al., *Scientific Data* 9:782, 2022 {#aybar2022}
- **Task:** cloud and cloud-shadow semantic segmentation in Sentinel-2.
- **Method:** a global, multi-temporal, hand-annotated dataset — 49,400 patches over 9,880 ROIs, with
  L1C and L2A multispectral data, Sentinel-1 SAR, auxiliary products, and the outputs of eight
  state-of-the-art cloud detection algorithms. Annotation tiers: **high-quality** (2,000 ROIs,
  pixel-level, ~150 min/image), **scribble** (2,000 ROIs, ~16 min/image), and **no-annotation**.
- **Relevance:** it defines the exact four-class problem this project solves — **clear, thick cloud,
  thin cloud, cloud shadow** — and supplies the expert-labelled tier we sample from.
- **Why it matters / limitation — the single most important source fact for this project:**
  the authors report human annotator agreement of **95.7% overall but only 78% producer's accuracy for
  thin cloud**, noting thin clouds "were always the source of the most contention" among annotators.
  Cloud shadow showed **21% disagreement** among expert reviewers, partly because thin low-altitude
  clouds cast shadows on the surface.
- **INTERPRETATION (ours):** if expert humans agree only ~78% of the time on thin cloud, then thin-cloud
  label noise is a floor on achievable model performance, and a model's thin-cloud IoU should not be
  read on the same scale as its clear-class IoU. This is our reasoning, not a claim of the paper.

### CloudSEN12+ — Aybar et al., *Data in Brief* 56:110852, 2024 {#aybar2024}
- **Task:** same four-class problem, extended.
- **Method:** more than 50,000 S2 patches; **doubles** the expert-labelled annotations of CloudSEN12;
  adds a larger 2000×2000 patch option (better shadow context) alongside 509×509; refined quality
  control corrected **452** mislabelled images. Class encoding **0=clear, 1=thick, 2=thin, 3=shadow**.
  Licensed **CC0** (public domain).
- **Relevance:** **this is the dataset this project actually uses.** Our bounded subset is drawn from
  the L1C collection, expert-labelled tier — see [`04_RESULTS.md`](04_RESULTS.md) for the exact
  provenance hash. The CC0 licence is why redistribution of derived artifacts is permissible, in
  contrast to the reference-only *On Cloud N* competition data ([ADR-0012](../docs/adr/ADR-0012-experimental-dataset-and-data-pipeline.md)).
- **Limitation:** a data descriptor, not a benchmarking study — it establishes the corpus and label
  protocol, not a model leaderboard. It therefore provides **no baseline number** we could compare
  against.

---

## 2. Architectures

### U-Net — Ronneberger, Fischer & Brox, MICCAI 2015, pp. 234–241 {#ronneberger2015}
- **Task:** biomedical image segmentation.
- **Method:** a contracting encoder for context and a symmetric expanding decoder for localisation,
  with skip connections that **concatenate** encoder features into the decoder. Heavy data augmentation
  lets it train end-to-end from very few annotated images.
- **Relevance:** our baseline ([ADR-0006](../docs/adr/ADR-0006-baseline-model-selection.md)). The
  concatenation-based skip is precisely the mechanism the improved model modifies.
- **Limitation for our task:** skips are fused **unweighted** — every encoder location contributes
  equally regardless of relevance.

### Attention U-Net — Oktay et al., MIDL 2018 (arXiv:1804.03999) {#oktay2018}
- **Task:** multi-class CT abdominal segmentation (pancreas — a small, low-contrast, variable target).
- **Method:** additive **attention gates (AGs)** inserted *into the skip connections*, learning to
  re-weight encoder features by relevance before concatenation. The stated aim is to "suppress
  irrelevant regions in an input image while highlighting salient features," removing the need for a
  cascaded localisation module while remaining computationally cheap.
- **Reported finding (source-derived):** AGs "consistently improve the prediction performance of U-Net
  across different datasets and training sizes."
- **Relevance:** the exact mechanism we adopt ([ADR-0010](../docs/adr/ADR-0010-improved-model-selection.md)),
  and the origin of our hypothesis.
- **Limitation — why the transfer is not automatic:** the evidence is on **abdominal CT**, a
  single-modality, single-sensor, anatomically-constrained domain. Nothing in this paper establishes a
  result for 13-band multispectral satellite imagery, for semi-transparent targets, or for classes whose
  boundaries are radiometric rather than anatomical. **We therefore treat "attention gates help thin
  cloud" strictly as a hypothesis to be tested, never as an inherited result** — the distinction
  ADR-0010 records and this project's M11 experiment exists to settle.

---

## 3. Cloud detection: classical baselines and where the difficulty lies

### Fmask — Zhu & Woodcock, *RSE* 118:83–94, 2012 {#zhu2012}
- **Task / method:** object-based cloud and cloud-shadow detection for Landsat; physically-motivated
  spectral tests producing a cloud probability, plus cloud–shadow geometric matching.
- **Relevance:** the reference point the whole field is measured against, and the reason our project
  treats cloud shadow as a *geometric* as well as spectral problem.
- **Limitation:** threshold-based and sensor-specific; the paper's own framing makes clear that
  semi-transparent cloud is not cleanly separable by fixed spectral thresholds.

### Fmask 4.0 — Qiu, Zhu & He, *RSE* 231:111205, 2019 {#qiu2019}
- **Method:** improved cloud/shadow detection across Landsats 4–8 **and Sentinel-2**.
- **Relevance:** shows the classical line was actively extended to Sentinel-2, i.e. our task has a
  strong non-deep-learning incumbent — a deep model must justify itself against it.
- **Limitation:** still rule-based; adaptation to a new sensor requires re-engineering rather than
  re-training.

### Comparison of cloud detection algorithms for Sentinel-2 — Tarrio et al., *Science of Remote Sensing* 2:100010, 2020 {#tarrio2020}
- **Task:** an independent comparison of cloud-detection algorithms on Sentinel-2.
- **Relevance:** demonstrates that **controlled, like-for-like comparison on identical evidence** is the
  accepted standard in this field — the standard our M11 fairness guardrails
  ([ADR-0011](../docs/adr/ADR-0011-model-comparison.md)) are built to meet.
- **Limitation:** compares existing operational algorithms; it is not a study of attention mechanisms
  and provides no number transferable to our architecture question.

### GCDB-UNet — Li et al., *Knowledge-Based Systems* 238:107890, 2022 {#li2022}
- **Task:** robust cloud detection in remote sensing imagery, **explicitly targeting thin cloud**.
- **Method:** a global context dense block embedded in U-Net, combining a **non-local self-attention**
  unit (to aggregate sparsely distributed thin cloud) with a squeeze-and-excitation channel unit.
- **Relevance — the closest prior work to our research question:** it independently identifies thin
  cloud as the failure mode of plain U-Net, and independently reaches for an **attention mechanism** as
  the remedy. Its stated motivation is that existing approaches fail on thin cloud "largely because of
  their small sizes and sparse distributions."
- **Limitation:** a different attention formulation (non-local + SE, on the backbone) from ours
  (additive gates, on the skips), on different datasets. It corroborates the *direction* of our
  hypothesis; it does not supply a baseline we can quote, and it is **not** evidence for our result.

---

## 4. Class imbalance in segmentation

### V-Net / Dice loss — Milletari, Navab & Ahmadi, 3DV 2016, pp. 565–571 {#milletari2016}
- **Method:** optimises a Dice-based objective directly, addressing the strong foreground/background
  imbalance typical of volumetric medical segmentation.
- **Relevance:** thin cloud is our rare class (**16.7%** of pixels in our subset, and the class the
  project is *about*), so imbalance-aware objectives are directly applicable.

### Generalised Dice loss — Sudre et al., DLMIA 2017, pp. 240–248 {#sudre2017}
- **Method:** class-rebalancing weights inside a Dice objective for **highly unbalanced** multi-class
  segmentation.
- **Relevance:** the natural next step for our loss ablation.
- **Status in this project:** **NOT EXECUTED.** Our M11 run used plain cross-entropy for both arms;
  loss configuration is an ablation dimension specified in [`03_ABLATION_TEMPLATE.md`](03_ABLATION_TEMPLATE.md)
  and not yet run. No claim is made about its effect.

---

## 5. Where this project sits

**Source-derived facts** establish: the four-class task and its expert-label difficulty
([#aybar2022](#aybar2022), [#aybar2024](#aybar2024)); U-Net's unweighted concatenation skip
([#ronneberger2015](#ronneberger2015)); attention gates as a skip-reweighting mechanism shown to help on
*medical* data ([#oktay2018](#oktay2018)); thin cloud as the field's recognised hard case, with an
independent group also applying attention to it ([#li2022](#li2022), [#zhu2012](#zhu2012)).

**The gap this project addresses (INTERPRETATION):** the attention-gate result is established on medical
imagery, and the thin-cloud-attention literature uses different attention formulations. Whether
*additive attention gates on skip connections* specifically help *thin cloud in multispectral Sentinel-2*
is not settled by any of the above.

**What this project contributes (PROJECT RESULT, bounded):** one controlled, fairness-guarded,
3-seed comparison of U-Net vs Attention U-Net on real expert-labelled CloudSEN12+ data, with per-class
results reported in full — including the class that got worse. The measured outcome is **MIXED**; see
[`04_RESULTS.md`](04_RESULTS.md). It is a bounded first experiment, **not** a benchmark, and it does not
compare against Fmask, GCDB-UNet, or any published number — those comparisons are **NOT EXECUTED**.
