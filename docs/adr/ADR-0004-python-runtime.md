# ADR-0004 — Python Runtime & Core Framework Versions

- **Status:** ACCEPTED (2026-08-06)
- **Milestone:** M1 (verified in M2)
- **Related:** Risk R-01 (dependency compatibility), R-15 (MPS), Assumption AS-05/D-F, ADR-0002

## Context

The host interpreter verified in M1 is **Python 3.14.2** (released too recently for the geospatial/ML wheel
ecosystem to have caught up). The project depends on binary-wheel packages that are historically slow to
support brand-new CPython releases: **`rasterio`, `GDAL`, `opencv-python`, `albumentations`**, and others.
Building these from source on macOS is fragile and time-consuming. PyTorch 2.11 is installed on the host, but
the **geospatial stack is the real compatibility risk**, and a mismatched interpreter would block Milestone 2
before any code runs.

## Decision

Pin the development environment to:

- **Python 3.11.x** for the entire backend / geo / ML stack (created as an isolated virtual environment; the
  host's 3.14 is **not** used for this project's stack).
- **PyTorch — latest stable release with Apple-Silicon (MPS) support**, selected/pinned in M2 against the
  chosen Python 3.11.x (exact version recorded in `requirements`/lockfile at M2, not guessed here).
- All other dependencies **version-pinned** in `requirements.txt` / lockfile for reproducibility (R-09).

## Rationale — why not Python 3.14

- **Wheel availability:** `rasterio`/`GDAL`/`albumentations`/`opencv` may not yet publish 3.14 wheels →
  source builds or install failure (R-01, H/H).
- **Ecosystem maturity:** 3.11 is a widely-supported, stable target with mature wheels across the geo/ML stack
  and well-tested PyTorch MPS builds (R-15).
- **Reproducibility:** pinning a mature interpreter reduces "works-on-my-machine" drift and makes the
  clean-environment rebuild (NFR-5) and Docker image (R-12) predictable.
- **No feature dependency on 3.12+/3.14** exists in the planned code.

## Consequences

- **Positive:** reliable installs, stable MPS, reproducible clean-env + Docker builds.
- **To manage:** the environment setup (M2) must create and document the 3.11 venv explicitly; CI and Docker
  must use the same pinned interpreter; version pins are re-verified whenever dependencies change.

## Verification owed (M2)

Confirm all geo/ML wheels install cleanly on Python 3.11.x and that a one-step PyTorch MPS training step runs;
record the exact pinned versions in `requirements`/lockfile.
