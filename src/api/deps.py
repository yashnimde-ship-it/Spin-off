"""Shared FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session

from src.db.session import SessionLocal


def get_db() -> Iterator[Session]:
    """Yield a database session for the lifetime of one request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
