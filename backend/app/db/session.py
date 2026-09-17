"""HexaCoders Polar Expedition Operations Platform - Database Session & Engine Scaffolding."""

from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from backend.app.core.config import settings

# Primary database engine using SQLAlchemy 2.0 with psycopg2
engine = create_engine(
    settings.get_database_url(),
    echo=(settings.LOG_LEVEL.upper() == "DEBUG"),
    future=True,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autocommit=False,
    autoflush=False
)


def get_db() -> Generator[Session, None, None]:
    """Dependency helper yielding database sessions."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def check_db_connectivity() -> bool:
    """Diagnostic health check verifying PostgreSQL connection status."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1;"))
            return result.scalar() == 1
    except Exception:
        return False
