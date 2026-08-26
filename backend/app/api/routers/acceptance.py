"""Acceptance route: GET /acceptance (Milestone 16 / D5).

Runs the acceptance harness on deterministic synthetic fixtures (isolated in-memory DB) and returns the D5
report. Thin adapter — no logic here. Real KPI/AC-4 acceptance is reported NOT YET MEASURED.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.acceptance import run_acceptance
from app.schemas.api import AcceptanceResponse

router = APIRouter(tags=["acceptance"])


@router.get("/acceptance", response_model=AcceptanceResponse)
def acceptance() -> AcceptanceResponse:
    report = run_acceptance()
    return AcceptanceResponse(**{k: report.to_dict().get(k) for k in AcceptanceResponse.model_fields})
