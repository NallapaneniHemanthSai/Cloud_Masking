"""Evaluation route: POST /evaluate (Milestone 13). Reuses the M8 framework."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_db
from app.db.base import Database
from app.schemas.api import EvaluateRequest, EvaluateResponse
from app.services import evaluation_service

router = APIRouter(tags=["evaluation"])


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate(req: EvaluateRequest, db: Database = Depends(get_db)) -> EvaluateResponse:
    out = evaluation_service.run_evaluation(
        db, mode=req.mode, dataset=req.dataset, split=req.split, seed=req.seed, synthetic=req.synthetic)
    return EvaluateResponse(**{k: out.get(k) for k in EvaluateResponse.model_fields})
