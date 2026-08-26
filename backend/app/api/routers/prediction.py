"""Prediction route: POST /predict (Milestone 13). Tiled inference via the M6/M4/M7 predictor."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_db
from app.db.base import Database
from app.schemas.api import PredictRequest, PredictResponse
from app.services import prediction_service

router = APIRouter(tags=["prediction"])


@router.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest, db: Database = Depends(get_db)) -> PredictResponse:
    out = prediction_service.run_prediction(
        db, architecture=req.architecture, in_channels=req.in_channels, num_classes=req.num_classes,
        encoder_depth=req.encoder_depth, base_channels=req.base_channels, device=req.device,
        patch_size=req.patch_size, checkpoint_path=req.checkpoint_path, image=req.image,
        synthetic=req.synthetic)
    return PredictResponse(**{k: out.get(k) for k in PredictResponse.model_fields})
