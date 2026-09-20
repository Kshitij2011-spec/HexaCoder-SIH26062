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
from backend.app.domains.inventory.router import router as inventory_router
from backend.app.domains.assets.router import router as assets_router
from backend.app.domains.incidents.router import router as incidents_router
from backend.app.domains.sync.router import router as sync_router
from backend.app.domains.operations.router import router as operations_router
from backend.app.domains.replanning.router import router as replanning_router
from backend.app.domains.control_tower.router import router as control_tower_router
from backend.app.platform.events.router import router as events_router
from backend.app.services.router import router as reasoning_router
from backend.app.db.session import get_db_health
from backend.app.core.config import settings
from backend.app.shared.schemas.envelope import ApiResponse, create_success_response

api_v1_router = APIRouter(prefix="/api/v1")
v1_router = APIRouter(prefix="/v1")


@api_v1_router.get("/health", response_model=ApiResponse, tags=["Health"])
@v1_router.get("/health", response_model=ApiResponse, tags=["Health"], include_in_schema=False)
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


# Mount owned domain and platform routers to both /api/v1 and /v1 (for proxy rewrite compatibility)
for r in (api_v1_router, v1_router):
    r.include_router(expeditions_router)
    r.include_router(missions_router)
    r.include_router(people_router)
    r.include_router(teams_router)
    r.include_router(time_windows_router)
    r.include_router(locations_router)
    r.include_router(transport_router)
    r.include_router(cargo_router)
    r.include_router(inventory_router)
    r.include_router(assets_router)
    r.include_router(incidents_router)
    r.include_router(sync_router)
    r.include_router(operations_router)
    r.include_router(replanning_router)
    r.include_router(events_router)
    r.include_router(reasoning_router)
    r.include_router(control_tower_router, prefix="/control-tower")

__all__ = ["api_v1_router", "v1_router"]
