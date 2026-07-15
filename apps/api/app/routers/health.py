"""Health-check router.

Kept intentionally dependency-free so it can be used as a liveness probe by the
frontend and the ``start-local`` scripts before any domain services exist.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
def health() -> dict[str, str]:
    """Return a static OK payload used to confirm the API is running."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.version,
    }
