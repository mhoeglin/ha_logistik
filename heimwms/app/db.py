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
    """Create all tables and apply additive column migrations.

    SQLModel.create_all() only creates missing tables, not missing columns
    on existing tables. For this small app we run a tiny idempotent migration
    that adds new columns (with defaults) to pre-existing SQLite tables.
    """
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    _migrate_add_columns(engine)


# (table, column, DDL type + default) — additive, idempotent migrations.
_ADDITIVE_COLUMNS: list[tuple[str, str, str]] = [
    ("location", "direction", "VARCHAR NOT NULL DEFAULT 'normal'"),
    ("item", "status", "VARCHAR NOT NULL DEFAULT 'stored'"),
    ("item", "lent_to", "VARCHAR"),
]


def _migrate_add_columns(engine: Engine) -> None:
    from sqlalchemy import text

    with engine.begin() as conn:
        for table, column, ddl in _ADDITIVE_COLUMNS:
            # PRAGMA table_info returns existing columns.
            rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
            existing = {r[1] for r in rows}
            if not existing:
                # table doesn't exist yet (fresh create handled it) -> skip
                continue
            if column not in existing:
                conn.exec_driver_sql(
                    f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"
                )


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a session."""
    with Session(get_engine()) as session:
        yield session
