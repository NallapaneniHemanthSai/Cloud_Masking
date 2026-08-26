"""System routes: /version, /health, /metrics (Milestone 13). Thin adapters over system_service."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.api import HealthResponse, MetricsResponse, VersionResponse
from app.services import system_service

router = APIRouter(tags=["system"])


@router.get("/version", response_model=VersionResponse)
def get_version() -> VersionResponse:
    return VersionResponse(**system_service.version_info())


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(**system_service.health_info(get_settings().database_url))


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics() -> MetricsResponse:
    return MetricsResponse(**system_service.metrics_snapshot())
