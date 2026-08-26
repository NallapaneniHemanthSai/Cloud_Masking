"""Training route: POST /train (Milestone 13). Bounded synthetic training via M7."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_db
from app.db.base import Database
from app.schemas.api import TrainRequest, TrainResponse
from app.services import training_service

router = APIRouter(tags=["training"])


@router.post("/train", response_model=TrainResponse)
def train(req: TrainRequest, db: Database = Depends(get_db)) -> TrainResponse:
    out = training_service.run_training(
        db, architecture=req.architecture, in_channels=req.in_channels, num_classes=req.num_classes,
        encoder_depth=req.encoder_depth, base_channels=req.base_channels, epochs=req.epochs,
        batch_size=req.batch_size, seed=req.seed, device=req.device, synthetic=req.synthetic,
        synthetic_patch=req.synthetic_patch, synthetic_batches=req.synthetic_batches)
    return TrainResponse(**{k: out.get(k) for k in TrainResponse.model_fields})
