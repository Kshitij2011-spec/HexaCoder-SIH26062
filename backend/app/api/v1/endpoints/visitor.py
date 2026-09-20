"""API router for anonymous, privacy-minimal visitor session notifications."""

import logging
from fastapi import APIRouter, BackgroundTasks, status

from backend.app.schemas.visitor import (
    VisitorCompleteRequest,
    VisitorEventRequest,
    VisitorSessionResponse,
)
from backend.app.services.mailgun_service import send_visitor_alert_email
from backend.app.services.visitor_session_service import visitor_session_manager

logger = logging.getLogger("cryos.visitor_api")

router = APIRouter(tags=["Visitor"])


@router.post(
    "/visitor/event",
    response_model=VisitorSessionResponse,
    status_code=status.HTTP_200_OK,
)
@router.post(
    "/api/visitor/event",
    response_model=VisitorSessionResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def record_visitor_event(
    event: VisitorEventRequest,
    background_tasks: BackgroundTasks,
) -> VisitorSessionResponse:
    """Record an anonymous visitor lifecycle event (start, heartbeat, route change)."""
    try:
        visitor_session_manager.record_event(
            session_id=event.session_id,
            route=event.route,
            event_type=event.event_type,
        )

        # Opportunistically finalize any expired sessions
        expired_payloads = visitor_session_manager.cleanup_and_finalize_expired()
        for payload in expired_payloads:
            background_tasks.add_task(
                send_visitor_alert_email,
                duration_seconds=payload["duration_seconds"],
                page_count=payload["page_count"],
                first_page=payload["first_page"],
                last_page=payload["last_page"],
                started_at=payload["started_at"],
            )
    except Exception as exc:
        logger.warning("Failed to record visitor event: %s", type(exc).__name__)

    return VisitorSessionResponse(ok=True)


@router.post(
    "/visitor/complete",
    response_model=VisitorSessionResponse,
    status_code=status.HTTP_200_OK,
)
@router.post(
    "/api/visitor/complete",
    response_model=VisitorSessionResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def complete_visitor_session(
    complete_req: VisitorCompleteRequest,
    background_tasks: BackgroundTasks,
) -> VisitorSessionResponse:
    """Finalize an anonymous visitor session and trigger notification if eligible."""
    try:
        payload = visitor_session_manager.complete_session(
            session_id=complete_req.session_id,
            route=complete_req.route,
        )

        if payload:
            background_tasks.add_task(
                send_visitor_alert_email,
                duration_seconds=payload["duration_seconds"],
                page_count=payload["page_count"],
                first_page=payload["first_page"],
                last_page=payload["last_page"],
                started_at=payload["started_at"],
            )
    except Exception as exc:
        logger.warning("Failed to complete visitor session: %s", type(exc).__name__)

    return VisitorSessionResponse(ok=True)
