"""HexaCoders Polar Expedition Operations Platform - Authoritative FastAPI Application."""

import time
import uuid
from typing import Callable
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError, DBAPIError

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.core.errors import DomainException
from backend.app.db.session import get_db_health
from backend.app.shared.schemas.envelope import (
    ApiResponse,
    ApiErrorItem,
    create_success_response,
    create_error_response,
)
from backend.app.api.router import api_v1_router

logger = get_logger("platform.main")

# Instantiate authorative FastAPI platform application
app = FastAPI(
    title="CRYOS — Polar Expedition Logistics Platform API",
    description=(
        "Authoritative application boundary for Antarctic & Polar Expedition Operational Logistics. "
        "Orchestrates expeditions, missions, teams, personnel, temporal constraints, and immutable operational events."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS configuration for authorized frontend consumers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def correlation_and_timing_middleware(request: Request, call_next: Callable) -> Response:
    """
    Request Correlation ID & Timing Middleware:
    - REQUEST ID (X-Request-ID): Traces single HTTP request lifecycle across network.
    - EVENT CORRELATION ID: Traces downstream operational domain mutation chain (distinct).
    Exposes X-Request-ID on all responses and logs structured request telemetry.
    """
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    # Attach to request state for downstream handlers
    request.state.request_id = request_id

    start_time = time.perf_counter()
    try:
        response: Response = await call_next(request)
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        logger.error(
            "Unhandled exception in request processing",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": round(duration_ms, 2),
                "error_type": exc.__class__.__name__
            },
            exc_info=True
        )
        raise exc

    duration_ms = (time.perf_counter() - start_time) * 1000.0
    response.headers["X-Request-ID"] = request_id

    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.1f}ms)",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
        }
    )
    return response


# Centralized Exception Handlers (Standardized Envelope Compliance)

@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException) -> JSONResponse:
    """Handles all domain-level business invariant and lifecycle transition errors."""
    request_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")
    error_item = ApiErrorItem(
        code=exc.code,
        message=exc.message,
        field=exc.field,
        details=exc.details
    )
    envelope = create_error_response([error_item], correlation_id=request_id)
    return JSONResponse(
        status_code=exc.status_code,
        content=envelope,
        headers={"X-Request-ID": request_id} if request_id else {}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handles Pydantic input schema validation errors without leaking sensitive data."""
    request_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")
    errors = []
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err.get("loc", []) if loc != "body")
        errors.append(ApiErrorItem(
            code="REQUEST_VALIDATION_ERROR",
            message=err.get("msg", "Invalid field value"),
            field=field if field else None,
            details={"type": err.get("type")}
        ))
    envelope = create_error_response(errors, correlation_id=request_id)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=envelope,
        headers={"X-Request-ID": request_id} if request_id else {}
    )


@app.exception_handler(SQLAlchemyError)
async def db_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Catches database level errors safely without leaking credentials or raw SQL."""
    request_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")
    logger.error(
        f"Database operation failed: {exc.__class__.__name__}",
        extra={"request_id": request_id, "error_type": exc.__class__.__name__},
        exc_info=True
    )
    error_item = ApiErrorItem(
        code="DATABASE_ERROR",
        message="An unexpected database error occurred. The transaction has been safely rolled back.",
        details={"error_type": exc.__class__.__name__}
    )
    envelope = create_error_response([error_item], correlation_id=request_id)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=envelope,
        headers={"X-Request-ID": request_id} if request_id else {}
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catches unhandled runtime exceptions and returns standard error envelope."""
    request_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")
    logger.error(
        f"Unhandled platform error: {str(exc)}",
        extra={"request_id": request_id, "error_type": exc.__class__.__name__},
        exc_info=True
    )
    error_item = ApiErrorItem(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected internal server error occurred.",
        details={"error_type": exc.__class__.__name__}
    )
    envelope = create_error_response([error_item], correlation_id=request_id)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=envelope,
        headers={"X-Request-ID": request_id} if request_id else {}
    )


# Root Health Check Endpoints

@app.get("/health", response_model=ApiResponse, tags=["Health"])
def root_health(request: Request):
    """Root operational health check reporting service status and safe database reachability."""
    db_health = get_db_health()
    overall_status = "HEALTHY" if db_health.get("status") == "HEALTHY" else "DEGRADED"

    health_info = {
        "application": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
        "status": overall_status,
        "database": db_health
    }
    return create_success_response(
        data=health_info,
        correlation_id=request.headers.get("X-Request-ID")
    )


# Mount versioned API v1 router
app.include_router(api_v1_router)
