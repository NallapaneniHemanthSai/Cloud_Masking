# Backend Scripts

Reproducibility scripts live here. **Milestone 2: placeholder only** — no scripts implemented yet.

Planned (per `docs/planning/07_MILESTONE_PLAN.md`), all path-agnostic and config-driven:

| Script | Milestone | Purpose |
|--------|-----------|---------|
| `download_cloudsen12.py` | M3 | Download the CloudSEN12 subset (primary dataset). |
| `download_on_cloud_n.py` | M3 | Download the On Cloud N reference benchmark. |
| `validate_dataset.py` | M3–M4 | Provenance / schema / CRS / bands / no-data validation. |
| `preprocess.py` | M4 | Bands, normalization, spectral indices, tiling, augmentation. |
| `split_dataset.py` | M4 | Spatial-block train/val/test split + leakage report. |
| `dataset_stats.py` | M4 | Class balance, per-band statistics, coverage. |
| `train.py` | M6–M7 | Train a model under a named profile (smoke/full). |
| `evaluate.py` | M8–M9 | Stratified evaluation + KPIs + guardrails. |
| `predict.py` | M13 | Run inference on a scene and emit masks/overlays. |
| `run_reference.sh` | M9 | One-command reproduction of the O2 reference (FR-2). |

No script is executed during Milestone 2.
