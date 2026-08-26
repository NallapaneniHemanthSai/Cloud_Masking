"""Upload service (Milestone 13).

Stores an uploaded file under the git-ignored ``outputs/uploads/`` directory with a content hash and
persists an :class:`UploadRow`. No raster parsing here (that is inference's job). Standard-library only.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.db.base import Database
from app.db.models import UploadRow


def _safe(name: str) -> str:
    return "".join(ch if (ch.isalnum() or ch in "._-") else "_" for ch in (name or "upload"))[:120]


def store_upload(db: Database, *, filename: str, content: bytes, content_type: str = "",
                 uploads_dir: Path | None = None) -> dict[str, Any]:
    """Persist ``content`` to disk (content-addressed) and record an :class:`UploadRow`."""
    content_hash = hashlib.sha256(content).hexdigest()
    dest = Path(uploads_dir) if uploads_dir else Path(get_settings().outputs_dir) / "uploads"
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"{content_hash[:12]}_{_safe(filename)}"
    path.write_bytes(content)
    with db.session() as s:
        row = UploadRow(upload_id=f"up-{content_hash[:12]}", filename=filename,
                        content_hash=content_hash, size_bytes=len(content), path=str(path),
                        content_type=content_type)
        s.add(row)
        s.flush()
        return row.to_dict()
