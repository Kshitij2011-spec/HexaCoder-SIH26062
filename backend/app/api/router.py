"""Central API Router for API v1."""

from fastapi import APIRouter, Request
from backend.app.domains.expeditions.router import router as expeditions_router
from backend.app.domains.missions.router import router as missions_router
from backend.app.domains.people.router import router as people_router
from backend.app.domains.teams.router import router as teams_router
from backend.app.domains.time_windows.router import router as time_windows_router
from backend.app.domains.locations.router import router as locations_router
from backend.app.domains.transport.router import router as transport_router
from backend.app.domains.cargo.router import router as cargo_router
from backend.app.platform.events.router import router as events_router
from backend.app.services.router import router as reasoning_router
from backend.app.db.session import get_db_health
from backend.app.core.config import settings
from backend.app.shared.schemas.envelope import ApiResponse, create_success_response

api_v1_router = APIRouter(prefix="/api/v1")


@api_v1_router.get("/health", response_model=ApiResponse, tags=["Health"])
def api_v1_health(request: Request):
    """API v1 diagnostic health endpoint providing safe operational metrics."""
    db_health = get_db_health()
    overall_status = "HEALTHY" if db_health.get("status") == "HEALTHY" else "DEGRADED"

    health_info = {
        "application": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
        "api_prefix": "/api/v1",
        "status": overall_status,
        "database": db_health
    }
    return create_success_response(
        data=health_info,
        correlation_id=request.headers.get("X-Request-ID")
    )


# Mount owned domain and platform routers
api_v1_router.include_router(expeditions_router)
api_v1_router.include_router(missions_router)
api_v1_router.include_router(people_router)
api_v1_router.include_router(teams_router)
api_v1_router.include_router(time_windows_router)
api_v1_router.include_router(locations_router)
api_v1_router.include_router(transport_router)
api_v1_router.include_router(cargo_router)
api_v1_router.include_router(events_router)
api_v1_router.include_router(reasoning_router)

__all__ = ["api_v1_router"]

