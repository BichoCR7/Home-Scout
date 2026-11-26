"""Alembic environment using the same URL parsing and SQLite safeguards as the app."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401 — registers all mapped tables in Base.metadata.
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import create_database_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
database_url = config.attributes.get("database_url") or get_settings().database_url


def run_migrations_offline() -> None:
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_database_engine(database_url, poolclass=NullPool)
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                render_as_batch=connection.dialect.name == "sqlite",
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
