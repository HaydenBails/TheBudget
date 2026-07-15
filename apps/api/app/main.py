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

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import dispose_database
from app.routers import accounts, health, profiles
from app.services import InvalidUpdateError, ResourceNotFoundError

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


@app.get("/", tags=["meta"], summary="Service metadata")
def root() -> dict[str, str]:
    """Return basic identifying metadata for the service."""
    return {
        "name": settings.app_name,
        "version": settings.version,
        "status": "ok",
    }
