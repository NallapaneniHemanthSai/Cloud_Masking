"""Model routes: GET /models, POST /models/register (Milestone 13)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_db
from app.db.base import Database
from app.models.config import ModelConfig
from app.schemas.api import ModelsResponse
from app.services import model_service

router = APIRouter(tags=["models"])


@router.get("/models", response_model=ModelsResponse)
def list_models(db: Database = Depends(get_db)) -> ModelsResponse:
    return ModelsResponse(architectures=model_service.list_architectures(),
                          registered_versions=model_service.list_registered(db))


@router.post("/models/register")
def register_model(config: dict, db: Database = Depends(get_db)) -> dict:
    model_config = ModelConfig.from_dict(config)
    return model_service.register_version(db, model_config)
