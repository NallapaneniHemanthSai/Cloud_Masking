# Risk Register

> **Deliverable ID:** D1 (partial) · **Milestone:** M1 · **Status:** DRAFT for approval
> Probability / Impact scale: **L** = Low, **M** = Medium, **H** = High.
> **Owner** = accountable role. Until the team (A-04) is assigned, all owners default to **PM** (project owner);
> role hints in parentheses indicate the intended owner once roles are assigned.
> **Status** ∈ {Open, Mitigating, Closed}.

---

| ID | Risk | Probability | Impact | Mitigation | Owner | Status |
|----|------|-------------|--------|------------|-------|--------|
| **R-01** | **Python dependency compatibility** — host Python is 3.14.2; `rasterio`/`GDAL`/`albumentations`/`opencv` may lack wheels → install fails. | H | H | Pin **Python 3.11.x** venv for the geo/ML stack (ADR-0004); verify wheel availability in M2 before scaffolding installs. | PM (DevOps) | Mitigating |
| **R-02** | **Long training time / no CUDA GPU** — Mac MPS/CPU only; DeepLabV3+/Attention U-Net train slowly. | H | M | Cap patch size (256×256), curated CloudSEN12 subset, gradient accumulation, `smoke`/`full` profiles, optional export to Colab/Kaggle. | PM (ML Lead) | Mitigating |
| **R-03** | **Sentinel-2 storage requirements** — full CloudSEN12 is tens of GB; laptop storage limited. | H | M | Use hand-labelled / high-quality subset + region-stratified sampling; tiled/streamed download; record exact subset + size budget (A-06). | PM (Data Lead) | Mitigating |
| **R-04** | **Spatial leakage** between train/val/test inflates metrics (violates NFR-4/AC-3). | M | H | Spatial-block splitting by scene/tile ID + geographic separation; automated leakage check in split report. | PM (Validation Lead) | Open |
| **R-05** | **Binary reference dataset cannot stratify** by thin cloud/snow/bright surface. | — | H | **Resolved:** CloudSEN12 primary (multi-class); On Cloud N kept as reference benchmark only (ADR-0001). | PM | Closed |
| **R-06** | **Change-detection source** (OSCD) may not spatially overlap chosen cloud scenes → weak O4 link. | M | H | Evaluate OSCD in M12; fallback controlled synthetic bi-temporal task with injected masking errors (ADR-0003). | PM (ML Lead) | Open |
| **R-07** | **Aggregate metric hides subgroup failure** (guardrail violation). | M | H | Mandatory per-subgroup + 95% CI reporting; guardrail fails the run if any critical subgroup underperforms (NT-1). | PM (Validation Lead) | Open |
| **R-08** | **Independent reviewer for O5** not secured. | M | H | Confirm reviewer at approval (A-03); design acceptance harness (D5) runnable by an external party. | PM | Open |
| **R-09** | **Reproducibility drift** (unpinned deps, unset seeds). | M | H | Pin all versions (lockfile), fixed seeds, scripted runbook, clean-env rebuild test in CI. | PM (DevOps) | Open |
| **R-10** | **Scope overrun** across 20 milestones in a two-semester window. | M | M | Milestone gating with hard stops; SegFormer OPTIONAL; MVP-per-milestone discipline. | PM | Open |
| **R-11** | **KL deployment stakeholder / decision owner undefined** (charter §4). | M | M | Escalate at approval; block O4/O5 sign-off until named (A-01). | PM | Open |
| **R-12** | **GDAL/rasterio system deps** in Docker differ from host → "works on my machine". | M | M | Base Docker image on a known geo image or pin GDAL install; clean-env build test. | PM (DevOps) | Open |
| **R-13** | **Domain shift between datasets** — model trained on CloudSEN12 degrades on On Cloud N (and vice-versa); band/label mismatch. | M | M | Keep datasets in distinct roles (primary vs reference benchmark); measure cross-dataset drop explicitly (C-6); document, don't hide. | PM (ML Lead) | Open |
| **R-14** | **Dataset availability & licensing** — CloudSEN12 / On Cloud N host, version, or licence may restrict download or redistribution of derived masks. | M | H | Verify licence + access at M3 (A-05); record in manifest; default to use-only (no redistribution) unless licence permits; mirror the exact version used. | PM (Data Lead) | Open |
| **R-15** | **Apple Silicon (MPS) compatibility** — some PyTorch ops unsupported/slow on MPS; possible numerical differences vs CPU/CUDA. | M | M | Verify a training step on MPS in M2; provide CPU fallback per-op (`PYTORCH_ENABLE_MPS_FALLBACK`); record device in every run; validate parity on a smoke case. | PM (ML Lead) | Open |
| **R-16** | **Thin-cloud class imbalance** — thin-cloud (and haze-like) pixels are rare vs clear/thick, biasing the model and inflating pixel accuracy. | H | H | Class-weighted / Dice loss, targeted sampling of thin-cloud tiles, report per-class IoU/F1 (never rely on pixel accuracy), monitor thin-cloud recall as a guardrail. | PM (ML Lead) | Open |
| **R-17** | **Annotation quality** — CloudSEN12 automatic/scribble labels and thin-cloud boundaries are noisy; On Cloud N labels may disagree. | M | M | Prefer hand-labelled high-quality subset; document label provenance/quality tier in manifest; note label noise as a limitation in results. | PM (Data Lead) | Open |

## Notes

- **R-01** and **R-02/R-15** are the most likely to block early progress and are addressed **first** in Milestone 2.
- **R-16** (thin-cloud imbalance) directly threatens the O2/O3 objectives and the NT-1 guardrail — tracked from M6.
- No risk is accepted silently; each has a named mitigation, owner, status, and a milestone where it is revisited.
- Required-by-review risks are all present: dataset availability/licensing (**R-14**), MPS compatibility (**R-15**),
  Python dependency compatibility (**R-01**), thin-cloud class imbalance (**R-16**), Sentinel-2 storage (**R-03**),
  long training time (**R-02**), annotation quality (**R-17**), domain shift between datasets (**R-13**).
