#!/usr/bin/env python3
"""Acceptance harness CLI (Milestone 16 / D5).

Runs the five mandatory negative tests (NT-1..NT-5) on deterministic **synthetic** fixtures, writes the
JSON/CSV/Markdown acceptance report, prints a per-NT summary, and **exits non-zero** if any NT fails or
falsely triggers — so it can gate CI. Real KPI/AC-4 acceptance is reported NOT YET MEASURED (never
fabricated). No training, no real data, no network.

Usage (project venv):
    backend/.venv/bin/python backend/scripts/run_acceptance.py --output outputs/acceptance
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.acceptance import export_acceptance_report, run_acceptance  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.logging_config import setup_logging  # noqa: E402

logger = logging.getLogger("run_acceptance")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    settings = get_settings()
    p = argparse.ArgumentParser(description="Run the D5 acceptance harness (NT-1..NT-5).")
    p.add_argument("--output", type=Path, default=settings.outputs_dir / "acceptance")
    p.add_argument("--log-level", default=settings.log_level)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    setup_logging(args.log_level)

    report = run_acceptance()
    written = export_acceptance_report(report, args.output / "acceptance_report")

    print()
    print("=== Acceptance harness (D5) — negative tests (SYNTHETIC fixtures) ===")
    for nt in report.nt_results:
        mark = "PASS" if nt.passed else "FAIL"
        print(f"  [{mark}] {nt.nt_id}  {nt.name}")
        print(f"         pass-fixture fired={nt.pass_case.triggered} (want False) | "
              f"fail-fixture fired={nt.fail_case.triggered} (want True)")
        if nt.fail_case.triggered:
            print(f"         action: {nt.fail_case.action}")
    print()
    print(f"SAFETY: {'PASS' if report.safety_passed else 'FAIL'}  | "
          f"KPI acceptance: {report.kpi_overall}  | overall: {report.overall}")
    print(f"content_hash={report.content_hash()[:12]}")
    print("NOTE: safety properties proven on SYNTHETIC fixtures; real KPI/AC-4 acceptance is NOT YET "
          "MEASURED; the M11 real-data conclusion remains MIXED.")
    logger.info("Reports: %s", ", ".join(str(p) for p in written.values()))
    return 0 if report.safety_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
