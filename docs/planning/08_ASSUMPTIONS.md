# Assumptions & Open Items Log

> **Milestone:** M1 · **Status:** DRAFT for approval
> Assumptions are recorded here **before** implementing. Open items marked "BLOCKING" must be resolved at
> the approval review; "NON-BLOCKING" items have a safe default and can be confirmed later.

---

## Confirmed decisions (from project owner, 2026-08-06)

| ID | Decision |
|----|----------|
| **D-A** | **Dual-dataset strategy (neither replaced):** primary = **CloudSEN12** (13-band Sentinel-2, multi-class: clear / thick cloud / thin cloud / cloud shadow) for multi-class detection + stratification; reference benchmark = **On Cloud N** (binary, 4-band) **reproduced** to validate published results + provide a domain-shift check. (ADR-0001) |
| **D-E** | **Haze = treated as thin cloud (approximated); removed as a separately measured objective** — no haze label in CloudSEN12, no standalone haze KPI; reported qualitatively within the thin-cloud stratum. (Charter §3.1) |
| **D-F** | **Runtime = Python 3.11.x** (pinned) with PyTorch stable + Apple-Silicon (MPS) support; host Python 3.14 is **not** used for the geo/ML stack. (ADR-0004) |
| **D-B** | **Compute = this Mac (Apple MPS / CPU).** Plan caps patch size, uses curated subsets, config-driven device auto-detection, smoke profile. (ADR-0002) |
| **D-C** | **Pacing = one milestone, hard stop.** Complete a milestone, output the 7-part summary, STOP for approval. |

## Assumptions (safe defaults, revisable)

| ID | Assumption | Rationale | Revisit |
|----|------------|-----------|---------|
| **AS-01** | Snow / bright surfaces are **not a separate label class** in CloudSEN12 — they appear as "clear". We stratify snow/bright-surface pixels using spectral criteria (NDSI, brightness) + region metadata, not a ground-truth "snow" class. | CloudSEN12 labels cloud types, not land cover. | M4 (validate the stratification proxy). |
| **AS-02** | **Haze is approximated as thin cloud** and folded into the thin-cloud stratum; it is **not a separately measured objective** and has **no standalone KPI** (decision D-E). There is no separate "haze" ground truth. A dedicated haze objective would require manual haze annotation (out of scope). | No dedicated haze label exists in CloudSEN12. | M9 (confirm the thin-cloud stratum meaningfully covers haze-like cases; document limitation — claim C-7). |
| **AS-03** | The change-detection downstream task will use an **external bi-temporal dataset (OSCD candidate)** or a **controlled synthetic bi-temporal fixture** if overlap is insufficient. | O4 needs measurable masking→change impact. | M12 (ADR-0003). |
| **AS-04** | Full-scale training may be **exported to Colab/Kaggle** if Mac MPS is too slow for DeepLabV3+; the codebase stays device-agnostic. | Feasibility on laptop. | M10. |
| **AS-05** | We pin **Python 3.11.x** for the geo/ML stack rather than use the host 3.14, to guarantee `rasterio`/`GDAL`/`albumentations` wheels and stable PyTorch MPS support. **Resolved as decision D-F.** | R-01, R-15. | M2 (verify wheels + MPS step) — ADR-0004. |
| **AS-06** | SQLite is the dev database; the schema is written to allow a later Postgres swap without domain-code changes. | Spec says SQLite in dev. | M13. |
| **AS-07** | SegFormer is **OPTIONAL** and only attempted if time permits after M11. | Spec marks it optional. | M10. |

## Open items requiring project-owner / reviewer confirmation

| ID | Item | Severity | Needed by |
|----|------|----------|-----------|
| **A-01** | **KL deployment stakeholder / operational decision owner** is unnamed (charter §4). | BLOCKING for O4/O5 sign-off | Approval review. |
| **A-02** | No sponsor/funder stated for the KL implementation. | NON-BLOCKING (record only) | Approval review. |
| **A-03** | **Independent reviewer** for O5 acceptance not yet secured. | BLOCKING for O5 | Before M19. |
| **A-04** | Team composition (3–4 members) & role ownership (spatial-evidence lead, model lead, GIS/delivery lead, registration/validation lead). If solo, single owner assumes all roles. | NON-BLOCKING | Before M6 (heavy work). |
| **A-05** | Confirm CloudSEN12 licence permits the intended use and redistribution of derived masks. | NON-BLOCKING (default: use-only, no redistribution) | M3. |
| **A-06** | Confirm storage budget on this Mac for the chosen CloudSEN12 subset. | NON-BLOCKING | M3. |

## How assumptions are handled

- Every assumption above is **testable** and is revisited at the listed milestone.
- If an assumption proves false, it triggers a documented decision (ADR update) — never a silent workaround.
- No assumption is used to fabricate a result; unmeasured quantities remain "NOT YET MEASURED".
