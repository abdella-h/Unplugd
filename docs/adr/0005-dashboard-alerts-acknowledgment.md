# ADR-0005: Dashboard alerts, scoped stream, and acknowledgment

**Status:** Accepted
**Date:** 2026-09-13

## Context

The dashboard service existed only as a global-admin SSE passthrough of raw
`device_status_changed` events: no persistence, no acknowledgment, no per-DC
filtering. The glossary already pins `Alert` (record raised on `warning` /
`alert`) and `Acknowledgment` (resolves the alert and resets the device to
`ok`), and ADR-0002 requires scoped admins to see/act only inside their
datacenter. This ADR records the first-cut shape agreed in the grilling
session before the endpoints were built.

## Decision

1. **Persisted `alerts` table in a separate dashboard DB** (no FK to devices —
   `device_id`/`datacenter_id` are copied event values). Columns: `device_id`,
   `datacenter_id`, `old_state`, `new_state`, `reporter`, `occurred_at`,
   `created_at`, `acknowledged_at`, `acknowledged_by`. Created via
   `Base.metadata.create_all()` like auth/devices; no migrations.

2. **Every `warning`/`alert` event persists; `ok` recoveries broadcast only.**
   No 5-minute dedupe on `device+status` and no manual `POST /alerts` fallback
   in this cut — both deferred until duplicates or broker outages are observed.

3. **SSE `/stream` is admin-only with per-event filtering:** global admin
   (`dc_id` null) sees all; scoped admin sees only its `datacenter_id`;
   operators get `403`. No `request.is_disconnected()` poll in the generator —
   it deadlocks httpx's ASGI transport in tests; disconnects are handled by
   generator cancellation with `unsubscribe()` in `finally`.

4. **Acknowledgment is `POST /alerts/{id}/acknowledge` (admin-only, scoped,
   idempotent).** It stamps `acknowledged_at/by`, commits even when the
   devices service is unreachable, best-effort resets the device via
   `PUT {DEVICES_SERVICE_URL}/devices/{id}/state {"state": "ok"}` forwarding
   the caller's Bearer token (devices re-enforces scope), reports
   `device_reset_ok` in the response, and broadcasts
   `alert_acknowledged_and_resolved` to all SSE subscribers.

## Consequences

- Ack survives a devices outage (alert marked, `device_reset_ok: false`) —
   operators may need to re-check a device whose reset failed.
- Replay of an SSE stream shows recoveries that have no alert row; clients
   must not assume every streamed event has a matching `GET /alerts` entry.
- Adding dedupe or manual alert creation later is a new ADR amending §2.
- Canonical naming reaffirmed: `services/dashboard` (`app.` package), roles
   `admin`/`operator`, states lowercase `ok`/`warning`/`alert`; `CLAUDE.md`'s
   `dash/`/`source/`/`guard`/`Ok` terms stay dropped.
