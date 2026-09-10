"""Shared FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.api.errors import DataNotLoaded
from src.db.session import SessionLocal


def get_db() -> Iterator[Session]:
    """Yield a database session for the lifetime of one request.

    A missing or unreachable database otherwise surfaces as a bare
    "Internal Server Error" with no body: the helpful RuntimeError raised by
    `settings.require_database_url()` is logged server-side and never reaches
    the caller. Wrapping it here covers every DB-backed endpoint at once
    rather than repeating the same try/except in four routers.
    """
    try:
        session = SessionLocal()
    except RuntimeError as exc:  # DATABASE_URL unset
        raise DataNotLoaded(
            detail=f"database unavailable: {exc}".split("\n")[0],
            remedy="set DATABASE_URL in .env at the repo root - see .env.example",
        ) from exc
    except SQLAlchemyError as exc:  # configured but unreachable
        raise DataNotLoaded(
            detail=f"database connection failed: {type(exc).__name__}",
            remedy="check DATABASE_URL in .env points at a reachable database",
        ) from exc

    try:
        yield session
    finally:
        session.close()
