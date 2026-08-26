"""Integration routes: /status, /recover, /lineage, /pipeline (Milestone 15).

Thin adapters over integration_service + lineage_service. Degraded mode + recovery are demonstrated here;
NT-5 lineage is queryable. No domain logic in the router.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_db
from app.db.base import Database
from app.schemas.api import (
    LineageResponse,
    PipelineRequest,
    PipelineResponse,
    RecoverResponse,
    StatusResponse,
)
from app.services import integration_service, lineage_service

router = APIRouter(tags=["integration"])


@router.get("/status", response_model=StatusResponse)
def status(db: Database = Depends(get_db)) -> StatusResponse:
    return StatusResponse(**integration_service.system_status(db))


@router.post("/recover/{event_id}", response_model=RecoverResponse)
def recover(event_id: str, note: str = Query(default=""), db: Database = Depends(get_db)) -> RecoverResponse:
    from app.core.exceptions import CloudMaskingError
    try:
        out = integration_service.recover(db, event_id, note=note)
    except CloudMaskingError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return RecoverResponse(**{k: out.get(k) for k in RecoverResponse.model_fields})


@router.get("/lineage", response_model=LineageResponse)
def lineage(limit: int = Query(default=100, ge=1, le=1000), db: Database = Depends(get_db)) -> LineageResponse:
    return LineageResponse(nodes=lineage_service.list_lineage(db, limit=limit))


@router.post("/pipeline", response_model=PipelineResponse)
def pipeline(req: PipelineRequest, db: Database = Depends(get_db)) -> PipelineResponse:
    out = integration_service.run_masking_pipeline(
        db, seed=req.seed, with_prediction=req.with_prediction,
        inject_guardrail_failure=req.inject_guardrail_failure)
    return PipelineResponse(**out)
