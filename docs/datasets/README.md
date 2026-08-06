# Dataset Documentation

Access, licensing, citation, and lifecycle documentation for the datasets. **Honesty policy:** metadata
is verified against official sources (see each doc's "Sources"); anything unconfirmed is marked
**"requires verification."**

| Doc | Contents |
|-----|----------|
| [`licenses.md`](licenses.md) | Licences, redistribution limits, citation requirements, usage restrictions (verified). |
| [`cloudsen12.md`](cloudsen12.md) | CloudSEN12 (primary) — versions, classes, bands, access, licence, citation. |
| [`on_cloud_n.md`](on_cloud_n.md) | On Cloud N (reference benchmark) — bands, labels, access, terms, citation. |

Metadata tables (bands, resolutions, class/label definitions) live in
[`../../data/metadata/`](../../data/metadata/); machine-readable provenance is in
[`../../data/manifests/datasets.yaml`](../../data/manifests/datasets.yaml).

## Dataset roles (ADR-0001)

- **CloudSEN12** — **primary** (13-band Sentinel-2, multi-class). Licence **CC0-1.0** (verified).
- **On Cloud N** — **reference benchmark** (4-band, binary). **Retained, not replaced.**
  **Redistribution prohibited** (verified).

## Provenance workflow

1. Read the per-dataset doc + `licenses.md`; complete any registration/agreement.
2. Confirm the exact version, licence, and access route; update `datasets.yaml` as needed.

## Verification workflow

Run `python backend/scripts/verify_datasets.py`. It validates the manifest (required fields) and prints a
structured status table per dataset (manifest / directory / download / checksum / completeness / overall).
Not-yet-downloaded datasets are `PENDING` (not a failure); use `--require-present` to enforce presence.

## Checksum workflow

`checksum` is a `TBD` placeholder until data is downloaded. After download, record a `sha256` per
artifact in `datasets.yaml`; verification then reports `VERIFIED` / `MISMATCH` (vs `UNAVAILABLE`).

## Dataset lifecycle

```
declare (manifest) → verify access/licence (docs) → download (scripts, manual steps) →
record download_date + checksum (manifest) → verify (verify_datasets.py) → preprocess (Milestone 4)
```
