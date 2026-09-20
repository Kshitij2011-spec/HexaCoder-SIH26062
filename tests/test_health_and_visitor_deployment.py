"""Tests for production deployment health checks (GET/HEAD /health) and visitor alert endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.visitor_session_service import visitor_session_manager


@pytest.fixture(autouse=True)
def reset_visitor_manager():
    """Reset visitor manager before each test."""
    visitor_session_manager.reset_state_for_tests()
    yield
    visitor_session_manager.reset_state_for_tests()


def test_head_health_returns_200_no_body():
    """Verify HEAD /health returns HTTP 200 with zero response body for uptime monitors."""
    client = TestClient(app)
    response = client.head("/health")
    assert response.status_code == 200
    assert response.text == ""
    assert len(response.content) == 0


def test_get_health_returns_200_with_cryos_identity():
    """Verify GET /health returns HTTP 200 with CRYOS application identity."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["errors"] is None
    assert body["data"]["application"] == "CRYOS"
    assert "status" in body["data"]
    assert "database" in body["data"]


def test_visitor_event_recording():
    """Verify anonymous visitor event is accepted and returns ok=True."""
    client = TestClient(app)
    # Start event
    res1 = client.post(
        "/visitor/event",
        json={
            "session_id": "00000000-1111-2222-3333-444444444444",
            "route": "/control-tower",
            "event_type": "start",
        },
    )
    assert res1.status_code == 200
    assert res1.json() == {"ok": True}

    # Route change
    res2 = client.post(
        "/api/visitor/event",
        json={
            "session_id": "00000000-1111-2222-3333-444444444444",
            "route": "/incidents",
            "event_type": "route",
        },
    )
    assert res2.status_code == 200
    assert res2.json() == {"ok": True}


def test_visitor_complete_recording():
    """Verify visitor completion is accepted and returns ok=True without failure."""
    client = TestClient(app)
    # Seed a session
    client.post(
        "/visitor/event",
        json={
            "session_id": "00000000-1111-2222-3333-555555555555",
            "route": "/inventory",
            "event_type": "start",
        },
    )

    # Complete session
    res = client.post(
        "/visitor/complete",
        json={
            "session_id": "00000000-1111-2222-3333-555555555555",
            "route": "/inventory",
        },
    )
    assert res.status_code == 200
    assert res.json() == {"ok": True}
