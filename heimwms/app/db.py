"""Database engine, session factory and initialisation."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# Import models so SQLModel.metadata is populated before create_all.
from app import models  # noqa: F401

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings.ensure_dirs()
        _engine = create_engine(
            settings.database_url,
            echo=settings.echo_sql,
            connect_args={"check_same_thread": False},
        )
    return _engine


def init_db() -> None:
    """Create all tables. Safe to call repeatedly."""
    SQLModel.metadata.create_all(get_engine())


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a session."""
    with Session(get_engine()) as session:
        yield session
