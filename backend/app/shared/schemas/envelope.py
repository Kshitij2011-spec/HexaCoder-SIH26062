"""Standard API Response Envelope Schemas conforming to docs/API_CONTRACT_POLICY.md."""

from datetime import datetime, timezone
from typing import Generic, List, Optional, TypeVar, Any, Dict
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Pagination metadata included in list responses."""
    page: int = Field(default=1, ge=1, description="Current 1-indexed page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    total_items: int = Field(default=0, ge=0, description="Total number of items matching filter")
    total_pages: int = Field(default=1, ge=0, description="Total number of pages")


class ApiMeta(BaseModel):
    """Top-level metadata envelope returned on every request."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of response")
    correlation_id: Optional[str] = Field(default=None, description="Request / Operational correlation tracing ID")
    version: str = Field(default="v1", description="API contract version")
    pagination: Optional[PaginationMeta] = Field(default=None, description="Pagination metadata when returning collections")


class ApiErrorItem(BaseModel):
    """Structured error object within errors array."""
    code: str = Field(description="Deterministic machine-readable error code")
    message: str = Field(description="Human-readable explanation of the failure")
    field: Optional[str] = Field(default=None, description="Request field that triggered error, if applicable")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Structured diagnostics or contextual parameters")


class ApiResponse(BaseModel, Generic[T]):
    """Authoritative API envelope returned on all 2xx and 4xx/5xx requests."""
    data: Optional[T] = Field(default=None, description="Primary payload or null on error")
    meta: ApiMeta = Field(default_factory=ApiMeta, description="Envelope metadata")
    errors: Optional[List[ApiErrorItem]] = Field(default=None, description="List of errors or null on success")


def create_success_response(
    data: Any,
    correlation_id: Optional[str] = None,
    pagination: Optional[PaginationMeta] = None
) -> Dict[str, Any]:
    """Helper constructing success response dictionary."""
    return {
        "data": data,
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": correlation_id,
            "version": "v1",
            "pagination": pagination.model_dump() if pagination else None,
        },
        "errors": None
    }


def create_error_response(
    errors: List[ApiErrorItem],
    correlation_id: Optional[str] = None
) -> Dict[str, Any]:
    """Helper constructing error response dictionary."""
    return {
        "data": None,
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": correlation_id,
            "version": "v1",
            "pagination": None,
        },
        "errors": [err.model_dump() for err in errors]
    }
