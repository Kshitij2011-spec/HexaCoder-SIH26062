# SIH26062 — API Contract & Endpoint Policy

## 1. Overview & Base Routing
All client-to-server communication adheres to strict RESTful JSON API conventions under a versioned root prefix:
```
/api/v1/
```

Direct, unversioned, or ad-hoc endpoint patterns are prohibited.

---

## 2. Standard Response Envelope

Every endpoint in the modular monolith returns a predictable, standardized envelope:

### 2.1 Success Response (`2xx`)
```json
{
  "data": {
    "id": "20000000-0000-0000-0000-000000000001",
    "code": "M-08",
    "title": "Coastal Geophysics Survey",
    "status": "READY",
    "derived_readiness": "READY",
    "data_provenance": "SYNTHETIC_DEMO"
  },
  "meta": {
    "timestamp": "2026-11-20T12:00:00Z",
    "correlation_id": "f0000000-0000-0000-0000-000000000000",
    "version": "v1"
  },
  "errors": null
}
```

### 2.2 Error Response (`4xx`, `5xx`)
```json
{
  "data": null,
  "meta": {
    "timestamp": "2026-11-20T12:01:00Z",
    "correlation_id": "f0000000-0000-0000-0000-000000000000",
    "version": "v1"
  },
  "errors": [
    {
      "code": "CONSTRAINT_VIOLATION",
      "message": "Assigned Snowcat PB-01 requires hydraulic hose maintenance before departure.",
      "field": "asset_id",
      "details": {
        "asset_code": "PB-01",
        "required_spare": "SKU-HYD-HOSE-08"
      }
    }
  ]
}
```

---

## 3. Shared Frontend API Client Rules

1. **Single Authorized Client**: The frontend interacts with backend APIs exclusively through the centralized API client in `frontend/src/lib/api/client.ts`.
2. **Responsibilities of the Shared Client**:
   - Manages base URL configuration (`VITE_API_BASE_URL`).
   - Injects JWT authentication headers (`Authorization: Bearer <token>`).
   - Injects tracing headers (`X-Correlation-ID`).
   - Normalizes errors and unhandled rejections into user-friendly notifications.
   - Handles network disconnection and queues mutations for offline sync.
3. **No Component-Level `fetch`**: Individual React components or feature views must **never** call native `fetch()` or `axios()` directly. All data fetching is orchestrated via TanStack Query hooks wrapping the shared client.
