#!/usr/bin/env python3
"""Download the On Cloud N dataset (REFERENCE BENCHMARK) — Milestone 3.

On Cloud N (DrivenData "Cloud Cover Detection Challenge") is the reference benchmark — **retained, not
replaced**. Its data-use terms **prohibit redistribution** and access requires registration/agreement.

This is a thin CLI: it delegates all argument parsing, manifest loading, downloading, and result
printing to :func:`scripts._dataset_cli.run`. It documents the manual access steps and never bypasses
registration, agreements, or authentication. No preprocessing.

Usage:
    python backend/scripts/download_on_cloud_n.py --dry-run
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the sibling helper module is importable regardless of cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _dataset_cli import run  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(run("on_cloud_n"))
