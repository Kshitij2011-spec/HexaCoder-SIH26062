import uuid
from datetime import date, datetime
from enum import Enum
from sqlalchemy.orm import declarative_base
from sqlalchemy import JSON, String, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID, JSONB

# Declarative base class for all SQLAlchemy ORM models.
# Tables are NOT created automatically from metadata; existing Supabase PostgreSQL schema is authoritative.
Base = declarative_base()


class SQLiteUUID(TypeDecorator):
    """
    SQLite-compatible UUID type that stores canonical hyphenated UUID strings (CHAR(36)).
    Ensures interoperability between ORM queries and raw SQL / seeded queries in SQLite tests.
    In PostgreSQL, native UUID is used unchanged.
    """
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if isinstance(value, uuid.UUID):
                return str(value)
            return str(uuid.UUID(str(value)))
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            if isinstance(value, uuid.UUID):
                return value
            return uuid.UUID(str(value))
        return None




def _json_safe(val):
    if val is None:
        return None
    if isinstance(val, uuid.UUID):
        return str(val)
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, Enum):
        return val.value
    if isinstance(val, dict):
        return {str(k): _json_safe(v) for k, v in val.items()}
    if isinstance(val, (list, tuple, set)):
        return [_json_safe(v) for v in val]
    return val


class SQLiteJSON(TypeDecorator):
    """
    SQLite-compatible JSON type that automatically serializes UUIDs, datetimes, and enums.
    In PostgreSQL, native JSONB is used unchanged.
    """
    impl = JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return _json_safe(value)
        return None

    def process_result_value(self, value, dialect):
        return value


# Multi-dialect column types: PostgreSQL native (production/dev authority) + SQLite fallback (unit tests)
PG_UUID = UUID(as_uuid=True).with_variant(SQLiteUUID(), "sqlite")
PG_JSON = JSONB().with_variant(SQLiteJSON(), "sqlite")

__all__ = ["Base", "PG_UUID", "PG_JSON", "SQLiteUUID", "SQLiteJSON"]

