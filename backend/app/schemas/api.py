"""Pydantic v2 request/response DTOs for the backend API (Milestone 13).

Thin data contracts between the FastAPI routers and the services. No domain logic. Pydantic is a required
M13 dependency (imported here, not in the ``app.schemas`` package ``__init__`` which stays stdlib-clean).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# --- system -------------------------------------------------------------------------------------
class VersionResponse(BaseModel):
    app_version: str
    model_version: str
    improved_model_version: str
    preprocessing_version: str
    visualization_version: str
    training_version: str
    evaluation_version: str
    failure_analysis_version: str
    comparison_version: str
    dataset_manifest_version: str
    python: str
    torch: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    torch_available: bool
    device: str
    database: str


class RouteMetric(BaseModel):
    route: str
    count: int
    error_count: int
    total_seconds: float
    avg_seconds: float
    last_seconds: float


class MetricsResponse(BaseModel):
    uptime_seconds: float
    total_requests: int
    total_errors: int
    routes: list[RouteMetric] = Field(default_factory=list)


# --- models -------------------------------------------------------------------------------------
class ModelInfo(BaseModel):
    architecture: str
    version: str
    description: str = ""
    aliases: list[str] = Field(default_factory=list)
    improves_over: str = ""
    supported_input_channels: list[int] = Field(default_factory=list)
    supported_output_classes: list[int] = Field(default_factory=list)


class ModelsResponse(BaseModel):
    architectures: list[ModelInfo] = Field(default_factory=list)
    registered_versions: list[dict[str, Any]] = Field(default_factory=list)


# --- training -----------------------------------------------------------------------------------
class TrainRequest(BaseModel):
    architecture: str = "unet"
    in_channels: int = 13
    num_classes: int = 4
    encoder_depth: int = 2
    base_channels: int = 8
    epochs: int = Field(default=1, ge=1, le=50)
    batch_size: int = Field(default=2, ge=1, le=64)
    seed: int = 42
    device: str = "cpu"
    synthetic: bool = True
    synthetic_patch: int = Field(default=16, ge=8, le=256)
    synthetic_batches: int = Field(default=2, ge=1, le=64)


class TrainResponse(BaseModel):
    run_id: str
    architecture: str
    status: str
    data_regime: str
    device: str
    epochs: int
    duration_seconds: float | None = None
    best_metric: float | None = None
    final_loss: float | None = None
    training_config_hash: str
    parameter_count: int | None = None
    notes: str = ""


# --- prediction ---------------------------------------------------------------------------------
class PredictRequest(BaseModel):
    architecture: str = "unet"
    in_channels: int = 13
    num_classes: int = 4
    encoder_depth: int = 2
    base_channels: int = 8
    device: str = "cpu"
    patch_size: int = Field(default=32, ge=8, le=512)
    checkpoint_path: str | None = None
    # Optional inline image (C,H,W) for JSON testing; otherwise a synthetic input is used.
    image: list[list[list[float]]] | None = None
    synthetic: bool = True


class PredictResponse(BaseModel):
    prediction_id: str
    architecture: str
    num_classes: int
    input_shape: list[int]
    output_shape: list[int]
    device: str
    data_regime: str
    class_pixel_counts: dict[str, int] = Field(default_factory=dict)
    source: str = ""
    notes: str = ""


# --- evaluation ---------------------------------------------------------------------------------
class EvaluateRequest(BaseModel):
    mode: str = "multiclass"
    dataset: str = "cloudsen12"
    split: str = "test"
    seed: int = 0
    synthetic: bool = True


class EvaluateResponse(BaseModel):
    evaluation_id: str
    dataset: str
    split: str
    data_regime: str
    pixel_accuracy: float | None = None
    macro_iou: float | None = None
    thin_cloud_iou: float | None = None
    per_class_iou: dict[str, float | None] = Field(default_factory=dict)
    config_hash: str = ""
    notes: str = ""


# --- upload / history ---------------------------------------------------------------------------
class UploadResponse(BaseModel):
    upload_id: str
    filename: str
    content_hash: str
    size_bytes: int
    content_type: str = ""
    path: str = ""


class HistoryResponse(BaseModel):
    training_runs: list[dict[str, Any]] = Field(default_factory=list)
    predictions: list[dict[str, Any]] = Field(default_factory=list)
    evaluations: list[dict[str, Any]] = Field(default_factory=list)
    uploads: list[dict[str, Any]] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    detail: str
    error_type: str = "error"
