# System Boundary & Permitted Scope

> **Deliverable ID:** D1 (partial) · **Milestone:** M1 · **Status:** DRAFT for approval

---

## 1. Included (in scope)

| # | Scope item | Objective |
|---|------------|-----------|
| 1 | **Reproducible reference**: stratify performance by thin cloud, haze, snow and bright surfaces. | O2 |
| 2 | **Differentiating contribution**: improve discrimination between cloud and bright surfaces such as snow. | O3 |
| 3 | **Integrated result**: quantify downstream impact of masking errors on a change-detection task. | O4 |
| 4 | **Independent acceptance**: validate stratified performance across regions and seasons, under representative, boundary, and failure conditions. | O5 |
| 5 | Full **engineering system**: dataset management, preprocessing, training, model comparison, evaluation, change detection, visualization, REST API, web app, logging, Docker deployment, testing, documentation, CI, reproducibility. | O1–O5 |

## 2. Explicitly Excluded (out of scope)

- Production certification, universal generalisation, unattended high-stakes operation **outside the
  validated envelope**.
- Any **isolated notebook, single model, single-function prototype, dashboard-only demo, or unvalidated
  library integration** presented as project completion.
- Real-time on-satellite / on-edge inference.
- Atmospheric correction research beyond what is needed for masking features.
- Non-optical sensors (SAR/radar) — Sentinel-2 optical only.

## 3. System Interface Boundary (from Architecture A — "what to build and connect")

```
INPUT           Multi-spectral satellite imagery + cloud annotations (CloudSEN12)
  │  validate provenance/CRS/units  (FR-1, NFR-3)
  ▼
REFERENCE       Stratify performance by thin cloud, haze, snow, bright surfaces  (O2)
  │  improve
  ▼
CONTRIBUTION    Discriminate cloud vs bright surface (snow)  (O3)
  │  integrate
  ▼
INTEGRATION     Quantify downstream impact of masking errors on change detection  (O4)
  │  operate / verify
  ▼
OPERATION       Cloud-masking system (API + web app), degraded mode + recovery
  │
  ▼
ASSURANCE       Spatial holdout + registration checks; independent acceptance  (O5)
```

Every arrow above is an **interface or evidence transfer** that must be implemented and tested
(unit + integration + system).

## 4. Validation Boundary (from Architecture B — "how to prove the result")

- Baseline (**O2**) and candidate (**O3**) are measured on the **same** evidence and the **same** frozen
  resource envelope (AC-4).
- Stress/challenge inputs (NT-1..5) are applied to both.
- Decision at the end: **Accept · Revise · Stop** — pass only when *every* target and guardrail passes.

## 5. Dependency Assumptions (must be confirmed at approval review)

- Access to **CloudSEN12 (primary, multi-class)** and **On Cloud N (reference benchmark, reproduced — not
  replaced)** datasets — see ADR-0001. Haze is approximated within the thin-cloud stratum (Charter §3.1).
- A change-detection evaluation source (candidate: OSCD — Onera Satellite Change Detection) — see ADR-0003 (deferred).
- Compute: this Mac (MPS/CPU) — see ADR-0002.
- An **independent reviewer** for O5 acceptance (domain/stakeholder/technical) — **NOT YET CONFIRMED**
  (open item A-03).

Unavailable dependencies require an **approved scope revision**, not a silent workaround.
