"""Pydantic schemas for anonymous, privacy-minimal visitor session alerts."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class VisitorEventRequest(BaseModel):
    """Event request payload for starting a session, heartbeat, or route navigation."""

    session_id: str = Field(
        ...,
        min_length=16,
        max_length=64,
        description="Anonymous client-generated session identifier (e.g. UUID)",
    )
    route: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Relative application route (e.g. '/control-tower')",
    )
    event_type: Literal["start", "heartbeat", "route"] = Field(
        ...,
        description="Type of session event",
    )

    model_config = ConfigDict(extra="forbid")


class VisitorCompleteRequest(BaseModel):
    """Payload sent when visitor leaves or session is finalized."""

    session_id: str = Field(
        ...,
        min_length=16,
        max_length=64,
        description="Anonymous client-generated session identifier",
    )
    route: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Last visited route before completion",
    )

    model_config = ConfigDict(extra="forbid")


class VisitorSessionResponse(BaseModel):
    """Standard response for visitor session endpoints."""

    ok: bool = True
