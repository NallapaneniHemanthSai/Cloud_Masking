# data/raw

Datasets as downloaded, before any preprocessing. **Contents are git-ignored** (only READMEs and
`.gitkeep` are tracked). Do not place processed patches here — those go in `data/processed/` (Milestone 4).

| Subdir | Dataset | Role |
|--------|---------|------|
| `cloudsen12/` | CloudSEN12 (13-band Sentinel-2, multi-class) | **Primary** |
| `on_cloud_n/` | On Cloud N (4-band, binary) | **Reference benchmark** (retained, not replaced) |

Populate via `backend/scripts/download_cloudsen12.py` and `backend/scripts/download_on_cloud_n.py`, then
validate with `backend/scripts/verify_datasets.py`. Provenance lives in `data/manifests/datasets.yaml`.
