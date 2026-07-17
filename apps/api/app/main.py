"""FastAPI application entrypoint.

Run locally with::

    uvicorn app.main:app --host 127.0.0.1 --port 8787

Local-first: uvicorn should bind to ``127.0.0.1`` so the API is not reachable
from other machines. There is no authentication layer by design — the product
is a single-user, local desktop tool.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings
from app.db import dispose_database
from app.middleware import ImportBodyLimitMiddleware
from app.routers import (
    accounts,
    budgets,
    categories,
    health,
    imports,
    income,
    profiles,
    recurring,
    transactions,
)
from app.services import (
    InvalidUpdateError,
    ResourceConflictError,
    ResourceNotFoundError,
    SplitSumError,
)

logger = logging.getLogger("spending_tracker.api")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Log startup and dispose lazily initialized database resources on exit."""
    logger.info(
        "%s v%s ready (local-first, bind %s:%s)",
        settings.app_name,
        settings.version,
        settings.host,
        settings.port,
    )
    try:
        yield
    finally:
        dispose_database()


app = FastAPI(
    title="Spending Tracker API",
    version=settings.version,
    summary="Local-first personal spending tracker backend.",
    lifespan=lifespan,
)

# Enforce import request bounds before routing or multipart form parsing.
app.add_middleware(ImportBodyLimitMiddleware)

# Allow the Vite dev server (both loopback spellings) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(profiles.router)
app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(budgets.router)
app.include_router(transactions.router)
app.include_router(recurring.router)
app.include_router(income.router)
app.include_router(imports.router)


@app.exception_handler(ResourceNotFoundError)
async def resource_not_found_handler(
    _request: Request,
    exc: ResourceNotFoundError,
) -> JSONResponse:
    """Map absent and out-of-scope resources to the same response shape."""

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


@app.exception_handler(InvalidUpdateError)
async def invalid_update_handler(
    _request: Request,
    exc: InvalidUpdateError,
) -> JSONResponse:
    """Return readable validation feedback for explicit null updates."""

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )


@app.exception_handler(ResourceConflictError)
async def resource_conflict_handler(
    _request: Request,
    exc: ResourceConflictError,
) -> JSONResponse:
    """Map a uniquely constrained duplicate to a 409 conflict."""

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(SplitSumError)
async def split_sum_handler(
    _request: Request,
    exc: SplitSumError,
) -> JSONResponse:
    """Return readable validation feedback for invalid split allocations."""

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )


@app.get("/api", tags=["meta"], summary="Service metadata")
def service_metadata() -> dict[str, str]:
    """Return basic identifying metadata for the service."""
    return {
        "name": settings.app_name,
        "version": settings.version,
        "status": "ok",
    }


# --- Serve the pre-built web UI (so the app runs with Python only, no Node) ----
# The React app is built to `apps/web/dist/` and committed. When present, the
# backend serves it on the same origin, so the whole app is one local process.
# API routes above are registered first and always take precedence; this SPA
# fallback only handles asset files and client-side routes (e.g. /app/...).
_WEB_DIST = Path(__file__).resolve().parents[3] / "apps" / "web" / "dist"

if (_WEB_DIST / "index.html").is_file():

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_web_app(full_path: str) -> FileResponse:
        """Serve a built asset if it exists, else the SPA entry (index.html)."""
        candidate = (_WEB_DIST / full_path).resolve()
        if full_path and _WEB_DIST in candidate.parents and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_WEB_DIST / "index.html")
