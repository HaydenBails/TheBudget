"""Alembic environment for the local SQLite database."""

from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy.engine import Connection

from alembic import context
from app.config import settings
from app.db import create_db_engine
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def database_url() -> str:
    """Return Alembic's URL form of the configured local SQLite path."""

    path = settings.database_path.expanduser().resolve()
    return f"sqlite:///{path.as_posix()}"


def run_migrations_offline() -> None:
    """Run migrations without opening a database connection."""

    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations(connection: Connection) -> None:
    """Run migrations using an existing connection."""

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with the application's configured SQLite engine."""

    engine = create_db_engine(settings.database_path)
    try:
        with engine.connect() as connection:
            run_migrations(connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
