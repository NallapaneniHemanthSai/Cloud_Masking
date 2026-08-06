# Data

Local dataset storage. **Contents are git-ignored** (only `.gitkeep` and this README are tracked).

| Subdir | Purpose | Populated in |
|--------|---------|--------------|
| `raw/` | Downloaded datasets as-acquired (CloudSEN12 primary, On Cloud N reference benchmark). | M3 |
| `processed/` | Preprocessed patches, spectral indices, and spatial-block splits. | M4 |
| `samples/` | Small, committable sample tiles for tests/visualization. | M4–M5 |

Paths are never hardcoded in code — the location is configured via `DATA_DIR` (see `backend/.env.example`)
and defaults to this directory. Provenance for every item is recorded in the dataset manifest (M3).
