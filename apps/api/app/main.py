"""FastAPI application entrypoint (Stage 0 placeholder).

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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health

logger = logging.getLogger("spending_tracker.api")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown hook. Logs a startup line; wire DB setup here later."""
    logger.info(
        "%s v%s ready (local-first, bind %s:%s)",
        settings.app_name,
        settings.version,
        settings.host,
        settings.port,
    )
    yield


app = FastAPI(
    title="Spending Tracker API",
    version=settings.version,
    summary="Local-first personal spending tracker backend (Stage 0 placeholder).",
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

# Future routers (profiles, accounts, imports, ...) are included alongside this
# one as later stages land.
app.include_router(health.router)


@app.get("/", tags=["meta"], summary="Service metadata")
def root() -> dict[str, str]:
    """Return basic identifying metadata for the service."""
    return {
        "name": settings.app_name,
        "version": settings.version,
        "status": "ok",
    }
