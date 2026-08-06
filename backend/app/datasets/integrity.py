"""Dataset integrity helpers (Milestone 3).

Checksum computation and file/directory existence checks used by the dataset verification workflow.
Standard-library only (``hashlib``, ``pathlib``) — no third-party dependencies, no preprocessing.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path

from app.core.constants import DEFAULT_CHECKSUM_ALGORITHM, DOWNLOAD_CHUNK_SIZE
from app.core.exceptions import DatasetError

logger = logging.getLogger(__name__)


def compute_checksum(
    path: Path,
    algorithm: str = DEFAULT_CHECKSUM_ALGORITHM,
    chunk_size: int = DOWNLOAD_CHUNK_SIZE,
) -> str:
    """Compute a hex digest for a file, streaming to bound memory.

    Args:
        path: File to hash.
        algorithm: Any name accepted by :func:`hashlib.new` (default ``"sha256"``).
        chunk_size: Read block size in bytes.

    Returns:
        The lowercase hex digest.

    Raises:
        DatasetError: If the file does not exist or the algorithm is unknown.
    """
    path = Path(path)
    if not path.is_file():
        raise DatasetError(f"Cannot checksum missing file: {path}")
    try:
        digest = hashlib.new(algorithm)
    except (ValueError, TypeError) as exc:  # unknown algorithm
        raise DatasetError(f"Unsupported checksum algorithm: {algorithm!r}") from exc

    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk_size), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_checksum(
    path: Path,
    expected: str,
    algorithm: str = DEFAULT_CHECKSUM_ALGORITHM,
) -> bool:
    """Return True if ``path``'s digest matches ``expected`` (case-insensitive).

    A blank/None ``expected`` means "no checksum available"; this returns ``False`` and the caller is
    expected to treat it as "unverified", not "corrupt".
    """
    if not expected:
        return False
    actual = compute_checksum(path, algorithm=algorithm)
    match = actual.lower() == expected.strip().lower()
    if not match:
        logger.warning("Checksum mismatch for %s (expected %s, got %s)", path, expected, actual)
    return match


@dataclass
class PathCheck:
    """Result of checking a set of expected paths under a base directory."""

    base: Path
    present: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when no expected path is missing."""
        return not self.missing


def check_paths_exist(base: Path, relative_paths: list[str]) -> PathCheck:
    """Check that each relative path exists under ``base``.

    Args:
        base: Base directory (e.g. a dataset's expected folder).
        relative_paths: Paths relative to ``base`` that should exist.

    Returns:
        A :class:`PathCheck` summarising present/missing entries.
    """
    base = Path(base)
    result = PathCheck(base=base)
    for rel in relative_paths:
        (result.present if (base / rel).exists() else result.missing).append(rel)
    return result


#: Tracked scaffolding files that are NOT dataset payload (so an empty-but-documented folder still
#: reads as "not downloaded").
NON_DATA_FILENAMES: frozenset[str] = frozenset({"README.md", ".gitkeep"})


def directory_summary(path: Path, ignore_names: frozenset[str] = NON_DATA_FILENAMES) -> dict:
    """Return a lightweight summary of a directory (file count + total bytes).

    Args:
        path: Directory to summarise.
        ignore_names: Filenames treated as non-data scaffolding and excluded from the counts.

    Non-recursive failures are handled gracefully; a missing directory yields zeros with ``exists=False``.
    """
    path = Path(path)
    if not path.is_dir():
        return {"exists": False, "file_count": 0, "total_bytes": 0}
    file_count = 0
    total_bytes = 0
    for item in path.rglob("*"):
        if item.is_file() and item.name not in ignore_names:
            file_count += 1
            try:
                total_bytes += item.stat().st_size
            except OSError:  # pragma: no cover - permission/race; keep counting
                logger.debug("Could not stat %s", item)
    return {"exists": True, "file_count": file_count, "total_bytes": total_bytes}
