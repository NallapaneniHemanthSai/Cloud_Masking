# Data

Local dataset storage. **Heavy dataset contents under `raw/`, `processed/`, and `external/` are
git-ignored** — only structure (`.gitkeep`), documentation (`README.md`), provenance (`manifests/`), and
metadata (`metadata/`) are tracked. Paths are configured via environment variables (see
`backend/.env.example`), never hardcoded.

## Layout

```
data/
├── raw/                 # datasets as-downloaded (git-ignored contents)
│   ├── cloudsen12/      # PRIMARY dataset (13-band Sentinel-2, multi-class)
│   └── on_cloud_n/      # REFERENCE BENCHMARK (4-band, binary) — retained, not replaced
├── processed/           # preprocessed patches/splits (git-ignored; populated in Milestone 4)
├── external/            # auxiliary/external reference layers (git-ignored contents)
├── manifests/           # provenance manifest(s): datasets.yaml  (tracked)
├── metadata/            # dataset metadata docs: bands, resolutions, class/label definitions (tracked)
└── samples/             # small committable sample tiles (tracked; added later)
```

## Environment overrides

| Variable | Default |
|----------|---------|
| `DATA_DIR` | `<project>/data` |
| `DATA_RAW_DIR` | `<DATA_DIR>/raw` |
| `DATA_EXTERNAL_DIR` | `<DATA_DIR>/external` |
| `DATA_MANIFESTS_DIR` | `<DATA_DIR>/manifests` |
| `DATA_METADATA_DIR` | `<DATA_DIR>/metadata` |

## Provenance workflow

1. Review provenance in [`manifests/datasets.yaml`](manifests/datasets.yaml).
2. Read the access/licence docs in [`../docs/datasets/`](../docs/datasets/) and complete any required
   registration/agreement (On Cloud N) or confirm the access route (CloudSEN12).
3. Run the download scripts (`backend/scripts/download_*.py`), then record the actual `download_date`
   and per-file `checksum` values back into `datasets.yaml`.
4. Validate with `backend/scripts/verify_datasets.py`.

Milestone 3 downloads nothing automatically: access details are marked **requires verification** and the
scripts document manual steps instead of bypassing them.
