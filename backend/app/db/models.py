"""SQLAlchemy ORM models (Milestone 13).

Persistence tables for model versions, training runs, predictions, evaluations, and uploads. Rows store
only metadata + hashes (no tensors, no raster payloads). Every row carries a ``created_at`` and a
``to_dict`` for API serialisation. SQLAlchemy 2.0 typed mappings.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ModelVersionRow(Base):
    """A registered model version (architecture + config hash + parameter count)."""

    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(String(128), index=True)
    architecture: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[str] = mapped_column(String(32))
    config_hash: Mapped[str] = mapped_column(String(64), index=True)
    parameter_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "model_id": self.model_id, "architecture": self.architecture,
                "version": self.version, "config_hash": self.config_hash,
                "parameter_count": self.parameter_count, "notes": self.notes,
                "created_at": self.created_at.isoformat() if self.created_at else None}


class TrainingRunRow(Base):
    """One training execution triggered through the API (reuses the M7 Trainer)."""

    __tablename__ = "training_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    experiment_id: Mapped[str] = mapped_column(String(128), default="")
    architecture: Mapped[str] = mapped_column(String(64), index=True)
    training_config_hash: Mapped[str] = mapped_column(String(64), index=True)
    dataset: Mapped[str] = mapped_column(String(64), default="")
    dataset_version: Mapped[str] = mapped_column(String(128), default="")
    data_regime: Mapped[str] = mapped_column(String(16), default="SYNTHETIC")
    seed: Mapped[int] = mapped_column(Integer, default=0)
    device: Mapped[str] = mapped_column(String(16), default="cpu")
    epochs: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="completed")
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    best_metric: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "run_id": self.run_id, "experiment_id": self.experiment_id,
                "architecture": self.architecture, "training_config_hash": self.training_config_hash,
                "dataset": self.dataset, "dataset_version": self.dataset_version,
                "data_regime": self.data_regime, "seed": self.seed, "device": self.device,
                "epochs": self.epochs, "status": self.status, "duration_seconds": self.duration_seconds,
                "best_metric": self.best_metric, "final_loss": self.final_loss, "notes": self.notes,
                "created_at": self.created_at.isoformat() if self.created_at else None}


class PredictionRow(Base):
    """One inference request served through the API."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prediction_id: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    architecture: Mapped[str] = mapped_column(String(64), default="")
    model_ref: Mapped[str] = mapped_column(String(128), default="")
    num_classes: Mapped[int] = mapped_column(Integer, default=0)
    input_shape: Mapped[str] = mapped_column(String(64), default="")
    output_shape: Mapped[str] = mapped_column(String(64), default="")
    device: Mapped[str] = mapped_column(String(16), default="cpu")
    data_regime: Mapped[str] = mapped_column(String(16), default="SYNTHETIC")
    source: Mapped[str] = mapped_column(String(256), default="")
    class_pixel_counts: Mapped[str] = mapped_column(Text, default="{}")   # JSON string
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        import json
        return {"id": self.id, "prediction_id": self.prediction_id, "architecture": self.architecture,
                "model_ref": self.model_ref, "num_classes": self.num_classes,
                "input_shape": self.input_shape, "output_shape": self.output_shape, "device": self.device,
                "data_regime": self.data_regime, "source": self.source,
                "class_pixel_counts": json.loads(self.class_pixel_counts or "{}"), "notes": self.notes,
                "created_at": self.created_at.isoformat() if self.created_at else None}


class EvaluationRunRow(Base):
    """One evaluation served through the API (reuses M8)."""

    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_id: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    dataset: Mapped[str] = mapped_column(String(64), default="")
    split: Mapped[str] = mapped_column(String(16), default="")
    model_id: Mapped[str] = mapped_column(String(128), default="")
    config_hash: Mapped[str] = mapped_column(String(64), default="")
    data_regime: Mapped[str] = mapped_column(String(16), default="SYNTHETIC")
    pixel_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    macro_iou: Mapped[float | None] = mapped_column(Float, nullable=True)
    thin_cloud_iou: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "evaluation_id": self.evaluation_id, "dataset": self.dataset,
                "split": self.split, "model_id": self.model_id, "config_hash": self.config_hash,
                "data_regime": self.data_regime, "pixel_accuracy": self.pixel_accuracy,
                "macro_iou": self.macro_iou, "thin_cloud_iou": self.thin_cloud_iou, "notes": self.notes,
                "created_at": self.created_at.isoformat() if self.created_at else None}


class UploadRow(Base):
    """An uploaded raster/file stored under the git-ignored uploads directory."""

    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    upload_id: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    filename: Mapped[str] = mapped_column(String(256))
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    path: Mapped[str] = mapped_column(Text, default="")
    content_type: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "upload_id": self.upload_id, "filename": self.filename,
                "content_hash": self.content_hash, "size_bytes": self.size_bytes, "path": self.path,
                "content_type": self.content_type,
                "created_at": self.created_at.isoformat() if self.created_at else None}
