"""Upload route: POST /upload (Milestone 13). Multipart file → git-ignored store + DB row."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_db
from app.db.base import Database
from app.schemas.api import UploadResponse
from app.services import upload_service

router = APIRouter(tags=["upload"])


@router.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...), db: Database = Depends(get_db)) -> UploadResponse:
    content = await file.read()
    out = upload_service.store_upload(db, filename=file.filename or "upload",
                                      content=content, content_type=file.content_type or "")
    return UploadResponse(**{k: out.get(k) for k in UploadResponse.model_fields})
