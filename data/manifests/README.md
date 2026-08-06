# data/manifests

Machine-readable dataset provenance. **Tracked in version control** (evidence, not heavy data).

- [`datasets.yaml`](datasets.yaml) — the authoritative provenance manifest, consumed by
  `backend/scripts/verify_datasets.py` and the download scripts, and parsed/validated by
  `app.datasets.manifest`.

## Schema (per dataset entry)

Every entry **must** declare these fields (validation fails otherwise):

| Field | Meaning |
|-------|---------|
| `dataset_id` | Stable machine key (matches the folder key). |
| `name` | Human-readable dataset name. |
| `version` | Dataset version/release. |
| `homepage` | Official homepage URL. |
| `source` | Where/how the data is obtained (host + tooling). |
| `official_paper` | Paper/DOI or benchmark write-up URL. |
| `citation` | Full citation string. |
| `license` | Licence (verified, or "requires verification"). |
| `redistribution` | Redistribution policy (e.g. permitted / prohibited). |
| `download_required` | Whether a download is needed (bool). |
| `manual_steps` | Ordered list of documented manual access steps. |
| `expected_directory` | Folder (relative to the data root) where files land. |
| `expected_size` | Approximate download size (verify at download). |
| `checksum_algorithm` | e.g. `sha256`. |
| `checksum` | Placeholder (`TBD`) until recorded after download. |
| `download_date` | Empty until first successful download (YYYY-MM-DD). |
| `bands` | Bands provided (structured). |
| `label_schema` | Label type + class encoding (structured). |
| `intended_use` | How the dataset is used in the project. |
| `notes` | Free-form verified notes / caveats. |

Optional: `role`, `download_urls` (empty when access is manual/authenticated), `expected_files`.

## Checksum workflow

`checksum` starts as `TBD`. After a real download, compute and record a `sha256` per artifact
(`compute_checksum` in `app.datasets.integrity`), then `verify_datasets.py` reports `VERIFIED` /
`MISMATCH`. Until a real value is recorded, integrity is reported as `UNAVAILABLE` (unverified, **not**
corrupt).

## After a download

Update `download_date` and the per-artifact `checksum` (and `expected_files`) here, then re-run
`backend/scripts/verify_datasets.py`.
