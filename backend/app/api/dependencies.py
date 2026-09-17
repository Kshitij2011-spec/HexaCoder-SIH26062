"""Common FastAPI API Dependencies."""

import uuid
from typing import Optional
from fastapi import Request, Depends
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.core.security import get_current_actor


def get_correlation_id(request: Request) -> uuid.UUID:
    """Extracts or generates an operational event correlation ID from request headers."""
    header_val = request.headers.get("X-Request-ID")
    if header_val:
        try:
            return uuid.UUID(header_val)
        except ValueError:
            pass
    return uuid.uuid4()


__all__ = ["get_db", "get_current_actor", "get_correlation_id"]
