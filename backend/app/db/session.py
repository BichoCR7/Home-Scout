"""SQLAlchemy engine and session-factory construction."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import Pool


def create_database_engine(
    database_url: str,
    *,
    echo: bool = False,
    poolclass: type[Pool] | None = None,
) -> Engine:
    """Create an engine for the supported SQLite and PostgreSQL configurations."""

    url = make_url(database_url)
    backend = url.get_backend_name()
    if backend not in {"sqlite", "postgresql"}:
        raise ValueError("Only SQLite and PostgreSQL database URLs are supported.")
    if backend == "postgresql" and url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    if backend == "postgresql" and url.drivername != "postgresql+psycopg":
        raise ValueError("PostgreSQL URLs must use the psycopg 3 driver.")

    options: dict[str, Any] = {"echo": echo, "pool_pre_ping": backend == "postgresql"}
    if poolclass is not None:
        options["poolclass"] = poolclass
    if backend == "sqlite":
        options["connect_args"] = {"check_same_thread": False}

    engine = create_engine(url, **options)
    if backend == "sqlite":

        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection: Any, _connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_session_factory(engine: Engine) -> Callable[[], Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
