#!/usr/bin/env python3
"""Generate exploratory-data-analysis (EDA) + quality-control (QC) reports for a dataset (Milestone 5).

Thin CLI: discovers a dataset, validates it, and writes a dataset EDA report (JSON/Markdown/CSV) and a QC
report (JSON/Markdown). It reads no pixels and trains nothing; if the dataset is not downloaded it still
produces a structural report (0 samples). Plotting degrades gracefully when matplotlib is unavailable.

Usage:
    python backend/scripts/eda_report.py --dataset on_cloud_n
    python backend/scripts/eda_report.py --dataset cloudsen12 --backend null
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.core.constants import DATASET_DIRNAMES, Dataset  # noqa: E402
from app.core.exceptions import CloudMaskingError  # noqa: E402
from app.core.logging_config import setup_logging  # noqa: E402
from app.preprocessing.loader import discover_samples, get_layout  # noqa: E402
from app.preprocessing.validation import validate_samples  # noqa: E402
from app.visualization.inspection import inspect_dataset  # noqa: E402
from app.visualization.qc import build_qc_report  # noqa: E402
from app.visualization.reports import build_dataset_report  # noqa: E402
from app.visualization.session import build_session  # noqa: E402

logger = logging.getLogger("eda_report")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Generate EDA + QC reports for a dataset.")
    parser.add_argument("--dataset", choices=[d.value for d in Dataset], required=True)
    parser.add_argument("--root", type=Path, default=None,
                        help="Dataset root (default: <DATA_RAW_DIR>/<dataset>).")
    parser.add_argument("--output-dir", type=Path, default=settings.outputs_dir / "reports")
    parser.add_argument("--log-level", default=settings.log_level)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    setup_logging(args.log_level)
    settings = get_settings()

    root = args.root or (settings.data_raw_dir / DATASET_DIRNAMES[Dataset(args.dataset)])
    created = datetime.now(timezone.utc).isoformat()

    try:
        layout = get_layout(args.dataset)
        discovery = discover_samples(root, layout)
        validation = validate_samples(discovery.samples)
        inspection = inspect_dataset(args.dataset, discovery.samples, validation_report=validation)

        dataset_report = build_dataset_report(inspection, created_utc=created)
        qc_report = build_qc_report(args.dataset, validation)

        out = Path(args.output_dir)
        written = dataset_report.save(out / f"{args.dataset}_eda", formats=("json", "md", "csv"))
        qc_md_path = out / f"{args.dataset}_qc.md"
        qc_md_path.parent.mkdir(parents=True, exist_ok=True)
        qc_md_path.write_text(qc_report.to_markdown(), encoding="utf-8")

        # The VisualizationSession is the primary object of the workflow.
        session = build_session(args.dataset, inspection, output_dir=str(out),
                                config={"dataset": args.dataset}, qc_report=qc_report.to_dict(),
                                timestamp=created)
        session.add_report("Dataset EDA", written)
        session.add_report("Quality control", {"md": qc_md_path})
        session_path = session.save_json(out / f"{args.dataset}_session.json")
    except CloudMaskingError as exc:
        logger.error("%s", exc)
        return 1

    if discovery.missing:
        logger.warning("Dataset '%s' not downloaded — report reflects an empty dataset.", args.dataset)
    logger.info("EDA report: %s", ", ".join(str(p) for p in written.values()))
    logger.info("QC report: %s", qc_md_path)
    logger.info("Session: %s (id=%s)", session_path, session.session_id)
    print()
    print(inspection.validation_summary.to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
