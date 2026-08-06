"""Backend application entry point (SCAFFOLD).

Milestone 2 provides only a harmless placeholder. The FastAPI application factory is intentionally not
implemented yet — FastAPI is a not-yet-installed dependency at Milestone 2, and application wiring
(routers, middleware, lifespan, logging bootstrap) is delivered in **Milestone 13 (Backend API)** per
``docs/planning/07_MILESTONE_PLAN.md``.

This module is kept import-clean (standard library only) so ``import app.main`` succeeds during the
Milestone 2 verification tests, and no runtime failure occurs merely from importing it.
"""

from __future__ import annotations


def create_app():
    """Placeholder for the FastAPI application.

    Implemented in Milestone 13. Returns ``None`` for now so importing and calling this module is
    side-effect free and cannot raise.

    Returns:
        None: until the FastAPI app factory is implemented in Milestone 13.
    """
    return None


if __name__ == "__main__":  # pragma: no cover - benign, does not affect imports.
    print(
        "Cloud Masking backend is scaffold-only at Milestone 2. "
        "The runnable app is implemented in Milestone 13."
    )
