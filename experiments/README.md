# Experiments

Curated experiment records for the Cloud Masking capstone. **Milestone 2: placeholder** — populated from
Milestone 7 onward as training/evaluation runs begin.

Intended contents:

- **Experiment logs** — per-run notes and configuration snapshots.
- **Ablation studies** — controlled add/remove experiments (e.g., spectral indices on/off) for O3.
- **Metric summaries** — aggregated KPI tables per model/profile.
- **Hyperparameter runs** — sweep records and selected configurations.

Relationship to other directories:

| Directory | Holds |
|-----------|-------|
| `experiments/` | Curated, human-readable experiment records and summaries (this directory). |
| `outputs/mlruns/` | Raw MLflow tracking store (git-ignored). |
| `reports/` | Formal evaluation/validation evidence reports. |

Heavy raw artifacts belong in `outputs/` (git-ignored); this directory keeps concise, committable records.
