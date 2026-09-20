"""In-memory, ephemeral visitor session manager for privacy-minimal operational alerts."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
import threading
from typing import Dict, List, Optional

from backend.app.core.config import settings

logger = logging.getLogger("cryos.visitor_session")

MAX_ACTIVE_SESSIONS = 1000
MAX_ROUTE_HISTORY = 25


@dataclass
class VisitorSession:
    """Ephemeral record of an anonymous browsing session."""

    session_id: str
    started_at: datetime
    last_active: datetime
    page_count: int
    route_sequence: List[str] = field(default_factory=list)
    last_route: str = "/"
    email_sent: bool = False


class VisitorSessionManager:
    """Thread-safe, in-memory session manager with single-send and rate-limiting guarantees."""

    def __init__(self) -> None:
        self._sessions: Dict[str, VisitorSession] = {}
        self._last_email_sent_at: Optional[datetime] = None
        self._lock = threading.Lock()

    def reset_state_for_tests(self) -> None:
        """Clear all in-memory sessions and cooldown state (for unit testing)."""
        with self._lock:
            self._sessions.clear()
            self._last_email_sent_at = None

    def record_event(self, session_id: str, route: str, event_type: str) -> None:
        """Record a visitor lifecycle event (start, heartbeat, or route change)."""
        now = datetime.now(timezone.utc)

        with self._lock:
            self._cleanup_stale_sessions_under_lock(now)

            session = self._sessions.get(session_id)
            if not session:
                # Enforce capacity limit
                if len(self._sessions) >= MAX_ACTIVE_SESSIONS:
                    self._evict_oldest_under_lock()

                self._sessions[session_id] = VisitorSession(
                    session_id=session_id,
                    started_at=now,
                    last_active=now,
                    page_count=1,
                    route_sequence=[route],
                    last_route=route,
                    email_sent=False,
                )
                logger.debug("Registered new anonymous visitor session: %s on %s", session_id[:8], route)
                return

            # Update existing session
            session.last_active = now

            if event_type == "route":
                if route != session.last_route:
                    session.page_count += 1
                    session.last_route = route
                    if len(session.route_sequence) < MAX_ROUTE_HISTORY:
                        session.route_sequence.append(route)
            elif event_type == "heartbeat":
                if route and route != session.last_route:
                    session.last_route = route

    def complete_session(self, session_id: str, route: Optional[str] = None) -> Optional[dict]:
        """Finalize an active session and determine if an alert email should be dispatched.

        Concurrency Guarantee:
        Reserves the email send (setting email_sent=True and updating cooldown timestamp)
        atomically under the lock before returning the payload to prevent double sends.
        """
        now = datetime.now(timezone.utc)

        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None

            if route:
                session.last_route = route
                session.last_active = now

            duration_seconds = max(0.0, (session.last_active - session.started_at).total_seconds())

            # Check 1: Single send per session
            if session.email_sent:
                return None

            # Check 2: Suppress immediate bounces (< 3 seconds and single page)
            if duration_seconds < 3.0 and session.page_count <= 1:
                logger.debug("Visitor alert suppressed: session was under 3s with single view.")
                return None

            # Check 3: Global alert cooldown
            if self._last_email_sent_at is not None:
                cooldown_delta = timedelta(minutes=settings.ALERT_COOLDOWN_MINUTES)
                if now - self._last_email_sent_at < cooldown_delta:
                    logger.info("Visitor alert suppressed by global cooldown.")
                    return None

            # Atomically reserve email dispatch
            session.email_sent = True
            self._last_email_sent_at = now

            first_page = session.route_sequence[0] if session.route_sequence else "/"
            return {
                "duration_seconds": duration_seconds,
                "page_count": session.page_count,
                "first_page": first_page,
                "last_page": session.last_route,
                "started_at": session.started_at,
            }

    def cleanup_and_finalize_expired(self) -> List[dict]:
        """Opportunistic sweep for abandoned sessions. Returns payloads for eligible alerts."""
        now = datetime.now(timezone.utc)
        eligible_payloads: List[dict] = []

        with self._lock:
            timeout = timedelta(minutes=settings.SESSION_TIMEOUT_MINUTES)
            eviction_age = timedelta(minutes=settings.SESSION_TIMEOUT_MINUTES * 2)
            expired_ids = []

            for sid, sess in list(self._sessions.items()):
                idle_time = now - sess.last_active

                if idle_time > timeout and not sess.email_sent:
                    duration_seconds = max(0.0, (sess.last_active - sess.started_at).total_seconds())

                    if duration_seconds >= 3.0 or sess.page_count > 1:
                        can_send = True
                        if self._last_email_sent_at is not None:
                            cooldown_delta = timedelta(minutes=settings.ALERT_COOLDOWN_MINUTES)
                            if now - self._last_email_sent_at < cooldown_delta:
                                can_send = False

                        if can_send:
                            sess.email_sent = True
                            self._last_email_sent_at = now
                            first_page = sess.route_sequence[0] if sess.route_sequence else "/"
                            eligible_payloads.append({
                                "duration_seconds": duration_seconds,
                                "page_count": sess.page_count,
                                "first_page": first_page,
                                "last_page": sess.last_route,
                                "started_at": sess.started_at,
                            })

                if idle_time > eviction_age:
                    expired_ids.append(sid)

            for sid in expired_ids:
                self._sessions.pop(sid, None)

        return eligible_payloads

    def _cleanup_stale_sessions_under_lock(self, now: datetime) -> None:
        """Remove sessions past double the session timeout."""
        eviction_age = timedelta(minutes=settings.SESSION_TIMEOUT_MINUTES * 2)
        stale_keys = [
            sid for sid, sess in self._sessions.items()
            if (now - sess.last_active) > eviction_age
        ]
        for sid in stale_keys:
            self._sessions.pop(sid, None)

    def _evict_oldest_under_lock(self) -> None:
        """Evict the least-recently active session when at capacity."""
        if not self._sessions:
            return
        oldest_id = min(self._sessions, key=lambda sid: self._sessions[sid].last_active)
        self._sessions.pop(oldest_id, None)


# Global singleton manager
visitor_session_manager = VisitorSessionManager()
