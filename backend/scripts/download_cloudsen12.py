#!/usr/bin/env python3
"""Download the CloudSEN12 dataset (PRIMARY dataset) — Milestone 3.

CloudSEN12 is the primary, multi-class Sentinel-2 dataset (clear / thick / thin cloud / cloud shadow).
This is a thin CLI: it delegates all argument parsing, manifest loading, downloading, and result
printing to :func:`scripts._dataset_cli.run`. All HTTP/download logic lives in
``app.datasets.download``; access controls are documented, never bypassed. No preprocessing.

Usage:
    python backend/scripts/download_cloudsen12.py --dry-run
    python backend/scripts/download_cloudsen12.py --output-dir /path/to/data/raw/cloudsen12
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the sibling helper module is importable regardless of cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _dataset_cli import run  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(run("cloudsen12"))
