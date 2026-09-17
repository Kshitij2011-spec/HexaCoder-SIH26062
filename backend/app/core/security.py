"""Actor Context and Security Scaffolding (Pre-Auth Foundation)."""

from typing import Dict, Any, Optional
from fastapi import Request


def get_current_actor(request: Optional[Request] = None) -> Dict[str, Any]:
    """
    Returns current request actor context for events and audit logging.
    In Phase 1.9/Track A foundation (prior to Phase 2 Auth implementation),
    actor is classified as SYSTEM or API with optional client IP provenance.
    No fake users or mock accounts are invented.
    """
    client_ip = request.client.host if request and request.client else "127.0.0.1"
    return {
        "actor_type": "SYSTEM",
        "actor_id": None,
        "source": "API",
        "client_ip": client_ip,
        "role": "SYSTEM_OPERATOR"
    }
