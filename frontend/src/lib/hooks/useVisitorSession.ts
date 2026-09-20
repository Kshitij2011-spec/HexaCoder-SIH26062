/**
 * Anonymous, privacy-minimal visitor session tracking hook for CRYOS owner notifications.
 *
 * Privacy Guarantees:
 * - Collects ZERO personally identifiable information (no IP, no user agent, no geolocation, no visitor identity).
 * - Ephemeral client-side session ID stored only in sessionStorage (destroyed on tab close).
 * - Silent network failure handling: network or Mailgun issues never impact the user experience.
 */

import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";

const SESSION_STORAGE_KEY = "cryos_session_id";
const HEARTBEAT_INTERVAL_MS = 30_000; // 30 seconds

function getOrCreateSessionId(): string {
  if (typeof window === "undefined") return "";

  try {
    const existing = window.sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (existing && existing.length >= 16 && existing.length <= 64) {
      return existing;
    }

    let newId: string;
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
      newId = crypto.randomUUID();
    } else {
      const bytes = new Uint8Array(16);
      crypto.getRandomValues(bytes);
      const b6 = bytes[6] ?? 0;
      const b8 = bytes[8] ?? 0;
      bytes[6] = (b6 & 0x0f) | 0x40;
      bytes[8] = (b8 & 0x3f) | 0x80;
      newId = Array.from(bytes, (b, i) =>
        (i === 4 || i === 6 || i === 8 || i === 10 ? "-" : "") +
        b.toString(16).padStart(2, "0")
      ).join("");
    }

    window.sessionStorage.setItem(SESSION_STORAGE_KEY, newId);
    return newId;
  } catch {
    return "";
  }
}

function getCurrentRoute(): string {
  if (typeof window === "undefined") return "/";
  const path = window.location.pathname || "/";
  const search = window.location.search || "";
  return `${path}${search}` || "/";
}

function postVisitorEvent(
  sessionId: string,
  route: string,
  eventType: "start" | "heartbeat" | "route"
): void {
  if (!sessionId) return;

  try {
    fetch("/api/visitor/event", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        session_id: sessionId,
        route,
        event_type: eventType,
      }),
      keepalive: true,
    }).catch(() => {
      // Non-critical notification: silent failure
    });
  } catch {
    // Non-critical notification: silent failure
  }
}

function sendCompleteBeacon(sessionId: string, route: string): void {
  if (!sessionId) return;

  try {
    const url = "/api/visitor/complete";
    const payload = JSON.stringify({
      session_id: sessionId,
      route,
    });

    if (typeof navigator !== "undefined" && typeof navigator.sendBeacon === "function") {
      const blob = new Blob([payload], { type: "application/json" });
      const sent = navigator.sendBeacon(url, blob);
      if (!sent) {
        fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: payload,
          keepalive: true,
        }).catch(() => {});
      }
    } else {
      fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: payload,
        keepalive: true,
      }).catch(() => {});
    }
  } catch {
    // Non-critical notification: silent failure
  }
}

/**
 * Tracks anonymous route transitions, heartbeats, and unload events for owner operational alerts.
 */
export function useVisitorSession(): void {
  const location = useLocation();
  const sessionIdRef = useRef<string>("");
  const initialStartSentRef = useRef<boolean>(false);
  const lastReportedRouteRef = useRef<string>("");
  const heartbeatTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 1. Initialize session and fire initial "start" event once
  useEffect(() => {
    const sessionId = getOrCreateSessionId();
    if (!sessionId) return;
    sessionIdRef.current = sessionId;

    if (!initialStartSentRef.current) {
      initialStartSentRef.current = true;
      const initialRoute = getCurrentRoute();
      lastReportedRouteRef.current = initialRoute;
      postVisitorEvent(sessionId, initialRoute, "start");
    }
  }, []);

  // 2. Track route navigation changes (react-router location changes)
  useEffect(() => {
    const sessionId = sessionIdRef.current || getOrCreateSessionId();
    if (!sessionId) return;
    sessionIdRef.current = sessionId;

    const currentRoute = getCurrentRoute();

    if (initialStartSentRef.current && currentRoute !== lastReportedRouteRef.current) {
      lastReportedRouteRef.current = currentRoute;
      postVisitorEvent(sessionId, currentRoute, "route");
    }
  }, [location.pathname, location.search]);

  // 3. Heartbeat management (30s interval, pauses when page is hidden) & Unload completion
  useEffect(() => {
    const startHeartbeat = () => {
      if (heartbeatTimerRef.current) clearInterval(heartbeatTimerRef.current);

      heartbeatTimerRef.current = setInterval(() => {
        if (document.visibilityState === "visible" && sessionIdRef.current) {
          postVisitorEvent(sessionIdRef.current, getCurrentRoute(), "heartbeat");
        }
      }, HEARTBEAT_INTERVAL_MS);
    };

    const stopHeartbeat = () => {
      if (heartbeatTimerRef.current) {
        clearInterval(heartbeatTimerRef.current);
        heartbeatTimerRef.current = null;
      }
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        startHeartbeat();
      } else {
        stopHeartbeat();
      }
    };

    const handlePageHide = () => {
      stopHeartbeat();
      if (sessionIdRef.current) {
        sendCompleteBeacon(sessionIdRef.current, getCurrentRoute());
      }
    };

    startHeartbeat();
    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("pagehide", handlePageHide);

    return () => {
      stopHeartbeat();
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("pagehide", handlePageHide);
    };
  }, []);
}
