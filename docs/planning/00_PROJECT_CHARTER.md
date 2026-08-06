# Project Charter — Cloud Masking Across Thin Cloud, Haze, Snow and Bright Surfaces

> **Deliverable ID:** D1 (partial) · **Milestone:** M1 — Project Planning · **Status:** DRAFT for approval
> **Date:** 2026-08-06 · **Institution:** KL University — Engineering Capstone (CP1 + CP2)

---

## 1. Problem Statement

Every satellite image analysis begins by discarding cloud-contaminated pixels. Cloud masking is
therefore an unglamorous but universal dependency of Earth observation. Its failures propagate
**silently**:

- A **thin cloud** left in the data becomes a spurious "change" in a change-detection task.
- A **snow field** wrongly masked as cloud becomes a permanent hole in the record.
- **Bright surfaces** (snow, sand, salt flats, rooftops) are spectrally close to cloud and are the
  hardest confusers.

The consequence is a spatial decision made from misaligned, incomplete, or weakly validated evidence.

## 2. Final Achievement Required

> Deliver cloud masking **validated on thin cloud, haze and snow**, with the **downstream impact of
> masking errors quantified** on a change-detection task.

## 3. Objective Ladder (O1–O5)

| ID  | Objective | Semester / Gate | Our concrete instantiation |
|-----|-----------|-----------------|----------------------------|
| **O1** | Validate the problem; freeze the engineering contract; build a baseline multi-spectral cloud segmentation and measure overall accuracy. | CP1 · Gate 1 | Baseline **U-Net** on CloudSEN12 patches; measure overall masking accuracy. |
| **O2** | Build the **reproducible reference**: stratify performance by thin cloud, haze, snow, bright surfaces. | CP1 · Gate 2 | One-command reproducible reference run + **stratified evaluation harness** over cloud-type / snow / bright-surface subgroups. *(Haze is approximated within the thin-cloud stratum — see §3.1.)* |
| **O3** | Engineer the **differentiating contribution**: improve discrimination between cloud and bright surfaces such as snow. | CP2 · Gate 3 | Improved model (**Attention U-Net / DeepLabV3+**) + spectral-index features (NDSI, cirrus) targeting the snow/bright-surface confusion. |
| **O4** | Integrate the **complete operable system**: quantify downstream impact of masking errors on a change-detection task. | CP2 · Gate 4 | Change-detection pipeline consuming masks; measure how masking errors change the detected-change score, with degraded mode + recovery. |
| **O5** | Independent acceptance: validate stratified performance **across regions and seasons**. | CP2 · Final Gate | Spatial-holdout, cross-region, cross-season validation report; all AC-1..4 + NT-1..5 executed. |

### 3.1 Dataset Strategy (both datasets retained — neither is replaced)

The project uses **two datasets with distinct, complementary roles**. On Cloud N is **not** replaced.

| Role | Dataset | Bands / labels | Purpose |
|------|---------|----------------|---------|
| **Primary dataset** | **CloudSEN12** | 13-band Sentinel-2; multi-class (clear / thick cloud / thin cloud / cloud shadow) | Multi-class cloud detection; O2 stratification (thin cloud, snow, bright surfaces); O3 cloud-vs-bright-surface contribution. |
| **Reference benchmark** | **On Cloud N** (DrivenData) | 4-band Sentinel-2 (B02,B03,B04,B08); binary cloud / no-cloud | **Reproduce published binary cloud-detection results** to validate pipeline correctness (FR-2 oracle), and provide a **cross-dataset domain-shift check** (Risk R-13). |

**Haze:** CloudSEN12 provides **no haze label**. Haze — an optically thin, low-opacity atmospheric
obscuration — is **treated as thin cloud (approximated)**: it is folded into the thin-cloud class and reported
**qualitatively within the thin-cloud stratum**. Haze is therefore **removed as a separately measured
objective** and carries **no standalone KPI**. A dedicated, separately-scored haze objective would require
manual haze annotation, which is out of current scope. (See `08_ASSUMPTIONS.md` AS-02 and `06_KPI_ACCEPTANCE.md`.)

## 4. Beneficiaries and Ownership (must be confirmed at approval)

- **Problem issuer / upstream custodian:** Radiant Earth Foundation (cited record). This is the *problem
  issuer*, **not** the KL deployment owner.
- **Primary beneficiaries (as cited):** Radiant Earth Foundation users, maintainers, and technical reviewers.
- **KL deployment stakeholder / operational decision owner:** **NOT YET CONFIRMED.**
  → **Approval condition:** the KL-side stakeholder and operational decision owner must be named before
  implementation proceeds. Recorded as open item **A-01** in `08_ASSUMPTIONS.md`.
- **Sponsor / funder:** none stated. Recorded as **A-02**.

## 5. Scope Summary (full detail in `02_SYSTEM_BOUNDARY.md`)

**In scope:** reproducible stratified reference (O2); cloud-vs-bright-surface contribution (O3); integrated
change-detection impact system (O4); independent cross-region/cross-season acceptance (O5); the full
engineering system (dataset mgmt, preprocessing, training, evaluation, API, web app, Docker, CI, docs).

**Out of scope:** production certification; universal generalisation; unattended high-stakes operation
outside the validated envelope; any isolated notebook / single model / dashboard-only demo counted as
"completion".

## 6. Success Definition

The project succeeds when **every** KPI target and guardrail in `06_KPI_ACCEPTANCE.md` passes under AC-1..AC-4,
**all five** negative tests (NT-1..NT-5) pass, and an independent reviewer confirms stratified performance
across regions and seasons — **or** the project is explicitly held/revised with documented rationale.
A pass may never be manufactured by an aggregate that hides a failing subgroup.

## 7. Non-Negotiable Working Rules (from project owner)

1. **No Git operations of any kind** are performed by the assistant — no commits, pushes, branches, history
   rewrites, author changes, or authentication. Git commands are only *suggested* as text.
2. The project owner is the **sole Git author** and manually reviews every file and creates every commit.
3. Work proceeds **one milestone at a time**; after each milestone the assistant STOPS and waits for
   explicit approval.
4. No fabricated results or invented metrics. Any unmeasured metric is stated as **"NOT YET MEASURED"**.
5. No simplification of the engineering scope; everything modular, explainable, reproducible.
