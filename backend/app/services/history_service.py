"""History service (Milestone 13).

Read-only queries over the persisted training/prediction/evaluation/upload rows for ``/history``. Newest
first, bounded by ``limit``. Standard-library + SQLAlchemy.
"""

from __future__ import annotations

from typing import Any

from app.db.base import Database
from app.db.models import EvaluationRunRow, PredictionRow, TrainingRunRow, UploadRow


def history(db: Database, *, limit: int = 50) -> dict[str, Any]:
    """Return the most recent rows from each history table (newest first)."""
    with db.session() as s:
        tr = s.query(TrainingRunRow).order_by(TrainingRunRow.created_at.desc()).limit(limit).all()
        pr = s.query(PredictionRow).order_by(PredictionRow.created_at.desc()).limit(limit).all()
        ev = s.query(EvaluationRunRow).order_by(EvaluationRunRow.created_at.desc()).limit(limit).all()
        up = s.query(UploadRow).order_by(UploadRow.created_at.desc()).limit(limit).all()
        return {
            "training_runs": [r.to_dict() for r in tr],
            "predictions": [r.to_dict() for r in pr],
            "evaluations": [r.to_dict() for r in ev],
            "uploads": [r.to_dict() for r in up],
        }
