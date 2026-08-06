# Source-to-Claim Map

> **Deliverable ID:** D1 (partial) · **Milestone:** M1 · **Status:** DRAFT for approval
> Purpose: for every claim we rely on, record the source, what it establishes, and what **we must
> independently verify** before building on it. Nothing here is treated as verified until the
> "verification status" column says so.

---

## 1. Cited Problem Source

| Field | Value |
|-------|-------|
| Evidence locator | "Satellite cloud detection" — DrivenData (the *On Cloud N: Cloud Cover Detection Challenge*). |
| Problem issuer / upstream custodian | Radiant Earth Foundation. |
| Sector | Agriculture, Environment & Sustainability. |
| What the source establishes | A reported, reproducible benchmark: segment cloud vs. non-cloud in Sentinel-2 imagery; overall accuracy dominated by easy pixels is a known failure mode. |
| Role in this project | **Reference benchmark — reproduced, not replaced.** On Cloud N is used to reproduce published binary cloud-detection results (validating pipeline correctness) and as a cross-dataset domain-shift check. CloudSEN12 is the primary multi-class dataset. |
| What we must verify | (a) current status & dataset version/availability; (b) reproduce the reported binary-masking behaviour; (c) record the gap between the source (binary, 4-band) and our primary multi-class scope (CloudSEN12). |
| Verification status | **NOT YET VERIFIED** — scheduled for M3. |

## 2. Claims → Sources → Verification

| # | Claim we depend on | Source | What we must independently check | Status |
|---|--------------------|--------|----------------------------------|--------|
| C-1 | On Cloud N provides Sentinel-2 imagery with binary cloud labels (B02,B03,B04,B08). | DrivenData challenge page; cloud-cover benchmark write-up; torchgeo docs. | Confirmed: 4 bands [B02,B03,B04,B08] from S2 L2A; 512×512 chips; binary labels; redistribution prohibited; 22,728 training chips. | **VERIFIED 2026-08-06** (exact label pixel encoding beyond {0,1} still requires verification at download). |
| C-2 | CloudSEN12 provides global 13-band Sentinel-2 patches with **multi-class** labels (clear / thick cloud / thin cloud / cloud shadow) suitable for O2 stratification. | Aybar et al., *CloudSEN12*, Scientific Data 9:782 (2022); CloudSEN12+ (Data in Brief 2024); HuggingFace `tacofoundation/cloudsen12` card. | Confirmed: classes 0/1/2/3 as above; L1C=13 bands (incl. B10 cirrus, B11/B12 SWIR), L2A=11+AOT+WVP; patches 509×509 & 2000×2000; CC0-1.0; global coverage. | **VERIFIED 2026-08-06** (curated subset + exact on-disk layout finalised in M4). |
| C-3 | NDSI = (B03 − B11)/(B03 + B11) separates snow from cloud; cirrus band B10 flags thin cloud. | Standard remote-sensing literature (to be cited in `paper/`). | Validate on CloudSEN12 snow scenes that these indices actually help; do not assume. | NOT YET VERIFIED |
| C-4 | A bi-temporal change-detection task is available to measure downstream masking impact (candidate: OSCD). | Daudt et al., OSCD (2018). | Confirm Sentinel-2 overlap, licence, and that masking errors measurably affect change scores. | NOT YET VERIFIED — ADR-0003 deferred to M12. |
| C-5 | "Overall accuracy dominated by easy pixels" masks poor performance on confusing cases. | Spec AC-2 / NT-1; cloud-masking literature. | Demonstrate empirically with a controlled fixture (NT-1). | NOT YET VERIFIED — M9. |
| C-6 | **Domain shift** exists between On Cloud N (4-band binary) and CloudSEN12 (13-band multi-class); a model trained on one degrades on the other. | This project's cross-dataset design; remote-sensing domain-adaptation literature. | Measure cross-dataset performance drop; do not assume magnitude. | NOT YET VERIFIED — M11 (Risk R-13). |
| C-7 | **Haze** can be adequately approximated as thin cloud for this project's objectives. | Charter §3.1 decision (no haze label in CloudSEN12). | Confirm the thin-cloud stratum meaningfully covers haze-like low-opacity cases; document limitation. | NOT YET VERIFIED — M9 (AS-02). |

## 3. Provenance / Evidence Manifest (to be produced in M3–M4)

For **every** dataset item, the manifest (D6) will record: source URL · access date · licence/permission ·
owner/custodian · record/sample/fixture IDs · exclusions · transformations · configuration · and the
objective/KPI that uses it. The AC-3 acceptance partition will be **reserved before O3 tuning** and separated
by an independent spatial unit so no transformation leaks acceptance information into development.

## 4. Honesty Statement

No result, metric, or benchmark value in this project is reported until it has been **measured** in our own
runs. Any value not yet measured is written explicitly as **"NOT YET MEASURED"**. Values from the cited
sources are labelled as *reported by source* and are not presented as our results.
