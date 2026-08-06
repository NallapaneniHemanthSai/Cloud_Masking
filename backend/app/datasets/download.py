"""Resumable file download helper (Milestone 3).

A dependency-free HTTP(S) downloader built on the standard library (``urllib``). Supports:

* **Resumable** downloads via HTTP Range requests (continues a partial ``*.part`` file when the server
  supports it; restarts cleanly otherwise).
* **Optional checksum verification** after completion.
* **Configurable** destination and timeout.
* **Graceful failure** — network/HTTP errors are wrapped in :class:`DatasetError` with actionable text;
  authentication failures (401/403) are reported, never bypassed.

This module performs **no preprocessing** and imposes no dataset-specific behaviour; the dataset scripts
decide *what* to download based on the provenance manifest.
"""

from __future__ import annotations

import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.constants import (
    DOWNLOAD_CHUNK_SIZE,
    HTTP_TIMEOUT_SECONDS,
    PARTIAL_DOWNLOAD_SUFFIX,
)
from app.core.exceptions import DatasetError
from app.datasets.integrity import verify_checksum

if TYPE_CHECKING:  # avoid a runtime import cycle; only needed for type hints.
    from app.datasets.manifest import DatasetRecord

logger = logging.getLogger(__name__)

# HTTP status codes referenced explicitly (avoid magic numbers).
_HTTP_OK = 200
_HTTP_PARTIAL_CONTENT = 206
_HTTP_UNAUTHORIZED = 401
_HTTP_FORBIDDEN = 403


def download_file(
    url: str,
    destination: Path,
    *,
    resume: bool = True,
    expected_checksum: str | None = None,
    timeout: int = HTTP_TIMEOUT_SECONDS,
    chunk_size: int = DOWNLOAD_CHUNK_SIZE,
) -> Path:
    """Download ``url`` to ``destination`` with optional resume and checksum verification.

    Args:
        url: Source URL (http/https).
        destination: Final file path. Parent directories are created if needed.
        resume: If True, continue a partial ``*.part`` download when the server allows it.
        expected_checksum: Optional expected sha256 hex digest; verified after download.
        timeout: Socket timeout in seconds.
        chunk_size: Streaming block size in bytes.

    Returns:
        The path to the completed file (``destination``).

    Raises:
        DatasetError: On any network/HTTP error, authentication requirement, or checksum mismatch.
    """
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    part_path = destination.with_name(destination.name + PARTIAL_DOWNLOAD_SUFFIX)

    if destination.exists():
        logger.info("File already present, skipping download: %s", destination)
        _maybe_verify(destination, expected_checksum)
        return destination

    existing_bytes = part_path.stat().st_size if (resume and part_path.exists()) else 0
    request = urllib.request.Request(url)
    if existing_bytes:
        request.add_header("Range", f"bytes={existing_bytes}-")
        logger.info("Resuming download of %s from byte %d", url, existing_bytes)
    else:
        logger.info("Starting download: %s -> %s", url, destination)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", _HTTP_OK)
            # If we asked to resume but the server ignored Range, restart from scratch.
            append = existing_bytes > 0 and status == _HTTP_PARTIAL_CONTENT
            mode = "ab" if append else "wb"
            if existing_bytes and not append:
                logger.info("Server did not honour Range; restarting download of %s", url)
            with part_path.open(mode) as out:
                written = existing_bytes if append else 0
                for block in iter(lambda: response.read(chunk_size), b""):
                    out.write(block)
                    written += len(block)
        logger.info("Downloaded %d bytes to %s", written, part_path)
    except urllib.error.HTTPError as exc:
        if exc.code in (_HTTP_UNAUTHORIZED, _HTTP_FORBIDDEN):
            raise DatasetError(
                f"Access to {url} requires authentication/agreement (HTTP {exc.code}). "
                "Follow the manual access steps documented in docs/datasets/ — do not bypass them."
            ) from exc
        raise DatasetError(f"HTTP error {exc.code} downloading {url}: {exc.reason}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise DatasetError(
            f"Network error downloading {url}: {exc}. Partial data kept at {part_path} for resume."
        ) from exc

    part_path.replace(destination)
    _maybe_verify(destination, expected_checksum)
    return destination


def _maybe_verify(path: Path, expected_checksum: str | None) -> None:
    """Verify a checksum if one was provided; log clearly when none is available."""
    if not expected_checksum:
        logger.warning("No checksum provided for %s — integrity UNVERIFIED.", path)
        return
    if verify_checksum(path, expected_checksum):
        logger.info("Checksum verified for %s", path)
    else:
        raise DatasetError(
            f"Checksum verification FAILED for {path}. Delete the file and re-download."
        )


# --------------------------------------------------------------------------------------------------
# Orchestration: decide what to download for a dataset record. Keeping this here means the CLI scripts
# contain no HTTP/download logic — they only parse args, call this, print the result, and exit.
# --------------------------------------------------------------------------------------------------

# Outcome status codes for a dataset download attempt.
STATUS_MANUAL_REQUIRED = "manual_access_required"
STATUS_DRY_RUN = "dry_run"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


@dataclass
class DownloadResult:
    """Structured outcome of :func:`download_dataset` (no printing here)."""

    dataset_id: str
    status: str
    output_dir: Path
    planned: list[str] = field(default_factory=list)     # URLs that were/would be fetched
    downloaded: list[str] = field(default_factory=list)  # files actually written
    manual_steps: list[str] = field(default_factory=list)
    message: str = ""

    @property
    def ok(self) -> bool:
        """True unless the attempt failed. Manual-access-required is a documented, non-error outcome."""
        return self.status != STATUS_FAILED


def download_dataset(
    record: "DatasetRecord",
    output_dir: Path,
    *,
    resume: bool = True,
    dry_run: bool = False,
) -> DownloadResult:
    """Download a dataset's artifacts as described by its manifest record.

    If the record has no direct ``download_urls`` (both project datasets require manual/authenticated
    access), this returns a :data:`STATUS_MANUAL_REQUIRED` result carrying the documented manual steps —
    it never bypasses access controls or fabricates a URL.

    Args:
        record: Validated dataset record from the manifest.
        output_dir: Destination directory for raw files.
        resume: Continue partial downloads when possible.
        dry_run: If True, plan the downloads without fetching.

    Returns:
        A :class:`DownloadResult` describing what happened.
    """
    output_dir = Path(output_dir)
    urls = record.download_urls or []

    if not urls:
        return DownloadResult(
            dataset_id=record.dataset_id,
            status=STATUS_MANUAL_REQUIRED,
            output_dir=output_dir,
            manual_steps=list(record.manual_steps),
            message=(
                "No direct download URL is recorded — this dataset requires manual/authenticated "
                "access. Follow the documented steps; access controls are not bypassed."
            ),
        )

    planned = [item["url"] for item in urls]
    if dry_run:
        return DownloadResult(
            dataset_id=record.dataset_id,
            status=STATUS_DRY_RUN,
            output_dir=output_dir,
            planned=planned,
            message=f"[dry-run] {len(planned)} file(s) would be downloaded to {output_dir}.",
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[str] = []
    for item in urls:
        url = item["url"]
        dest = output_dir / item.get("filename", Path(url).name)
        try:
            download_file(url, dest, resume=resume, expected_checksum=item.get("checksum"))
        except DatasetError as exc:
            return DownloadResult(
                dataset_id=record.dataset_id,
                status=STATUS_FAILED,
                output_dir=output_dir,
                planned=planned,
                downloaded=downloaded,
                message=str(exc),
            )
        downloaded.append(str(dest))

    return DownloadResult(
        dataset_id=record.dataset_id,
        status=STATUS_COMPLETED,
        output_dir=output_dir,
        planned=planned,
        downloaded=downloaded,
        message=f"Downloaded {len(downloaded)} file(s) to {output_dir}.",
    )
