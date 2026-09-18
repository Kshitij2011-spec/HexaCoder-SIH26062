"""SQLAlchemy Declarative Base for HexaCoders Polar Platform."""

from sqlalchemy.orm import declarative_base
from sqlalchemy import Uuid, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB

# Declarative base class for all SQLAlchemy ORM models.
# Tables are NOT created automatically from metadata; existing Supabase PostgreSQL schema is authoritative.
Base = declarative_base()

# Multi-dialect column types: PostgreSQL native (production/dev authority) + SQLite fallback (unit tests)
PG_UUID = UUID(as_uuid=True).with_variant(Uuid(as_uuid=True), "sqlite")
PG_JSON = JSONB().with_variant(JSON(), "sqlite")

__all__ = ["Base", "PG_UUID", "PG_JSON"]
