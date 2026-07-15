"""SQLAlchemy engine and session construction.

Construction is explicit so tests and future services can inject an isolated
database rather than touching the user's configured local store.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def create_db_engine(database_path: Path) -> Engine:
    """Create a SQLite engine for ``database_path`` with WAL enabled.

    The containing directory is created on first engine construction. SQLite
    itself creates the database file only when the first connection is opened.
    """

    resolved_path = database_path.expanduser().resolve()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{resolved_path.as_posix()}")

    @event.listens_for(engine, "connect")
    def configure_sqlite(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a typed session factory bound to ``engine``."""

    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
