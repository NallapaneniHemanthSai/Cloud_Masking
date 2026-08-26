"""History route: GET /history (Milestone 13)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_db
from app.db.base import Database
from app.schemas.api import HistoryResponse
from app.services import history_service

router = APIRouter(tags=["history"])


@router.get("/history", response_model=HistoryResponse)
def history(limit: int = Query(default=50, ge=1, le=500), db: Database = Depends(get_db)) -> HistoryResponse:
    return HistoryResponse(**history_service.history(db, limit=limit))
