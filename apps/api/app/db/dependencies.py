"""FastAPI database dependencies with caller-scoped transactions."""

from __future__ import annotations

from collections.abc import Iterator
from threading import Lock

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.session import create_db_engine, create_session_factory

_initialization_lock = Lock()
_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_session() -> Iterator[Session]:
    """Yield one transaction per request, committing only successful requests."""

    session_factory = _get_session_factory()
    with session_factory.begin() as session:
        yield session


def dispose_database() -> None:
    """Dispose lazily initialized application database resources."""

    global _engine, _session_factory
    with _initialization_lock:
        if _engine is not None:
            _engine.dispose()
        _engine = None
        _session_factory = None


def _get_session_factory() -> sessionmaker[Session]:
    global _engine, _session_factory
    if _session_factory is None:
        with _initialization_lock:
            if _session_factory is None:
                _engine = create_db_engine(settings.database_path)
                _session_factory = create_session_factory(_engine)
    return _session_factory
