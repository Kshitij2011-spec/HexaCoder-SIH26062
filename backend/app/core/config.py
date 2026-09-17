"""HexaCoders Polar Expedition Operations Platform - Core Configuration."""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and database connection parameters."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Environment
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    PROJECT_NAME: str = "HexaCoders - SIH26062"
    API_V1_STR: str = "/api/v1"
    API_BASE_URL: str = "http://localhost:8000/api/v1"

    # Database Configuration (PostgreSQL / Supabase)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "hexacoders_polar"
    DATABASE_URL: Optional[str] = Field(
        default=None,
        description="Direct PostgreSQL connection string"
    )
    SUPABASE_DB_URL: Optional[str] = Field(
        default=None,
        description="Direct Supabase PostgreSQL connection string"
    )

    # Supabase platform settings
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None

    def get_database_url(self) -> str:
        """Return canonical database URL."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        if self.SUPABASE_DB_URL:
            return self.SUPABASE_DB_URL
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"



settings = Settings()
