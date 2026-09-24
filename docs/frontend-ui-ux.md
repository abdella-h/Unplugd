# Unplugd Frontend UI/UX Direction

**Status:** Implemented
**Date:** 2026-09-23

## Purpose

Unplugd should feel like a dependable enterprise monitoring console rather than a
stock administration template. The interface will prioritize fast recognition,
clear operational scope, and safe incident action while remaining truthful to the
current human-reported Device State model.

The product name remains **Unplugd**. The visual identity changes, but the
underlying domain language remains canonical: Datacenter, Device, State,
Operator, Admin, Alert, Open Alert, and Acknowledgment.

## Current baseline

The current frontend is a Nuxt 3 SPA using stock `@nuxt/ui` and Tailwind
defaults. It has no authored design system, logo, application layout, dark-first
theme, or mobile navigation. Authenticated pages repeat a simple header and use
stock cards, forms, and tables.

The existing application supports:

- fleet counts by Datacenter and Device State;
- human-reported `ok`, `warning`, and `alert` States;
- Device inventory and scoped access;
- persisted Alerts and Acknowledgment;
- an authenticated dashboard SSE stream;
- Global Admin, Scoped Admin, and Operator authorization.

It does not have Device telemetry, time-series history, uptime, latency,
utilization, broker-health reporting, or a durable record of failed device reset
attempts. The redesign must not imply that those capabilities exist.

## Goals

- Establish a recognizable Unplugd visual identity.
- Provide a persistent, role-aware application shell.
- Make operational risk and freshness immediately visible.
- Support fast triage, inventory navigation, and scoped action.
- Improve desktop density without sacrificing laptop or mobile usability.
- Replace generic loading, empty, error, and confirmation experiences.
- Preserve existing authorization and introduce no fake monitoring data.
- Make all accepted behavior verifiable by automated checks.

## Non-goals

- Adding telemetry collection or chart libraries.
- Inventing trends, forecasts, uptime, availability, or online/offline state.
- Replacing Nuxt, Vue, TypeScript, Tailwind, or `@nuxt/ui`.
- Adding a global command palette before the product has enough destinations to
  justify one.
- Building tenant, Site, Incident, Notification, or Fleet domain concepts.
- Persisting failed reset outcomes or exposing RabbitMQ health in this release.
- Turning the public authentication pages into authenticated dashboard routes.

## Product principles

1. **Calm and trustworthy.** Alarm colors are reserved for real operational
   State and retain their established green/amber/red meaning.
2. **Operations before administration.** Alert triage and current fleet health
   lead the experience; inventory and Datacenter management follow.
3. **Scope is always visible.** Users should never have to infer which
   Datacenter context they are viewing.
4. **Data remains visible when stale.** A failed refresh does not erase the last
   useful operational view.
5. **Actions state their consequences.** Acknowledgment and Device reset are
   separate outcomes.
6. **No invented certainty.** The UI reports what the APIs know and labels
   freshness precisely.
7. **Dense, not cramped.** Desktop uses compact information architecture without
   reducing legibility or removing labels.

## Information architecture

### Monitor

- **Overview** — fleet State, Open Alerts, and Datacenter health.
- **Alerts** — Admin-only Open and Acknowledged Alert workflows.

### Infrastructure

- **Devices** — scoped Device inventory, search, filtering, and investigation.
- **Datacenters** — Global Admin-only management.

Unauthorized sections are hidden, not shown disabled.

### Role visibility

| Route | Operator | Scoped Admin | Global Admin |
|-------|----------|--------------|--------------|
| Overview | Yes | Yes | Yes |
| Devices | Yes | Yes | Yes |
| Alerts | No | Yes | Yes |
| Datacenters | No | No | Yes |

Navigation grouping is presentational. Backend authorization remains the security
boundary.

### Datacenter context

- Global Admin: fixed **All datacenters** context. No interactive switcher is
  introduced in this release.
- Scoped Admin: fixed assigned Datacenter name.
- Operator: fixed assigned Datacenter name.
- An unscoped Operator remains unauthorized and receives the existing `403`.

To provide names rather than numeric identifiers, `GET /datacenters` will return:

- all Datacenters to a Global Admin;
- only the assigned Datacenter to a Scoped Admin or Operator;
- `401` to anonymous callers.

Datacenter mutation remains Global Admin-only.

## Application shell

### Sidebar

- Expanded width: 240px.
- Collapsed width: 72px.
- Mobile: off-canvas drawer.
- The preference is persisted locally as a UI preference, separate from auth
  state.
- Brand and primary navigation remain at the top.
- User identity and logout remain in the lower shell.
- Collapsed mode retains icons and accessible tooltips.
- Active navigation uses shape, text, and color rather than color alone.

### Top bar

The top bar contains only persistent context that applies across pages:

- current page title;
- fixed Datacenter context;
- last successful data-fetch time;
- Realtime channel state for Admins;
- user menu with explicit role and logout action.

It does not contain global search in this release. A missing Realtime channel is
not shown to Operators because they are not permitted to subscribe.

### User menu

Role labels are explicit:

- **Global Admin**
- **Scoped Admin**
- **Operator**

Scoped users also see their assigned Datacenter. Username remains the primary
identity because the current session does not guarantee profile metadata.

## Visual identity

### Brand

The product retains the Unplugd name and gains:

- a geometric `U` monogram formed from inspection brackets and a status aperture;
- a stronger wordmark with deliberate tracking and weight;
- a consistent mark treatment in the sidebar, authentication pages, and browser
  metadata.

The mark must not imply that Devices self-report or transmit telemetry.

### Color tokens

The brand accent is cyan-teal. It is never used to mean healthy, and it does not
replace State colors.

| Semantic token | Dark value | Light value | Use |
|----------------|------------|-------------|-----|
| Canvas | `#080D16` | `#F3F6FA` | Application background |
| Surface | `#101827` | `#FFFFFF` | Panels and tables |
| Raised surface | `#172033` | `#F8FAFC` | Menus, dialogs, hover surfaces |
| Border | `#28364C` | `#D7DFEA` | Dividers and focused containment |
| Primary text | `#F8FAFC` | `#0F172A` | Headings and values |
| Muted text | `#94A3B8` | `#526174` | Supporting text |
| Brand accent | `#22D3EE` | `#0E7490` | Navigation, focus, primary action |
| Accent foreground | `#082F49` | `#FFFFFF` | Text on brand accent |

Semantic State colors remain:

| State | Base | Light-theme text-safe variant |
|-------|------|-----------------------------|
| `ok` | `#22C55E` | `#15803D` |
| `warning` | `#F59E0B` | `#B45309` |
| `alert` | `#EF4444` | `#B91C1C` |

State backgrounds are low-emphasis tints. Every State is represented by an icon,
text, and color.

### Typography

Use a locally bundled Inter variable font; no runtime request to an external font
service is permitted.

- Page title: 24px / 30px, semibold.
- Section title: 16px / 24px, semibold.
- KPI value: 28px / 34px, semibold, tabular numerals.
- Body and controls: 14px / 20px.
- Dense table content: 12px / 18px.
- Metadata and captions: 12px / 16px.

### Geometry and elevation

- Base spacing unit: 4px, using an 8px rhythm for primary layout gaps.
- Control radius: 6px.
- Panel radius: 8px.
- Dialog radius: 10px.
- Borders and surface contrast define hierarchy first.
- Shadows are reserved for overlays and floating controls.
- Stock large, soft, rounded cards are replaced with compact operational panels.

## Page direction

### Overview

Overview is the primary monitoring surface.

1. **KPI strip**
   - Total Devices;
   - `ok` Devices;
   - `warning` Devices;
   - `alert` Devices;
   - Open Alerts for Admins, including zero.
2. **Attention panel**
   - newest and most severe Open Alerts;
   - direct navigation to the Alert and related Device;
   - Operators receive Device-focused attention content instead of forbidden
     Alert data.
3. **Datacenter health table**
   - one row per visible Datacenter, including Datacenters with zero Devices;
   - Device count and compact State distribution;
   - scoped and accurate naming;
   - no large donut-card grid.
4. **Freshness**
   - record a successful API fetch time;
   - show stale state and Retry after a failed refresh;
   - preserve the prior data.

Labels describe “reported Device States,” not uptime.

### Devices

The Devices page is a compact operational inventory.

- Search by Device name, type, and serial number.
- Filter by Device State and Datacenter where authorized.
- Sort by operational relevance and inventory fields.
- Paginate client-side at 25 rows per page.
- Link the row to `/devices/:id`.
- Keep State editing explicit and role-authorized.
- Show per-row pending and error feedback.
- Replace native confirmations with application dialogs.
- Show custom filtered, empty, loading, and failure states.
- On mobile, render purposeful compact rows rather than a horizontally scrolling
  table.

### Device detail

`/devices/:id` presents available truth only:

- Device name and current State;
- Datacenter;
- type and serial number;
- description and record timestamps;
- State report action;
- Admin edit action.

It does not show fabricated history, telemetry, current Reporter, or trend charts.
A missing or out-of-scope Device receives a branded error state consistent with
the API response.

### Alerts

Alerts default to **Open**.

- Navigation exposes the Open Alert count for Admins.
- Tabs separate Open and Acknowledged Alerts.
- Dense rows emphasize severity, Device, Datacenter, transition, time, Reporter,
  and Acknowledgment.
- Global Admins can filter by Datacenter; Scoped Admins remain server-scoped.
- Acknowledgment has an explicit pending state.
- Successful Acknowledgment without a successful reset displays:
  **Alert acknowledged; device reset failed**.
- Retry Reset repeats the Acknowledgment request during the current browser
  session when an immediate reset failure is known.
- Reset retry state is not shown after reload because the current backend does
  not persist the outcome.
- The frontend never treats the `alert_acknowledged_and_resolved` event name as
  proof that the Device reached `ok`.

### Datacenters

Global Admin management retains existing capabilities but adopts the shared
visual system.

- Search and sort the Datacenter inventory.
- Use the shared CRUD dialog patterns.
- Require typed confirmation for deletion.
- Explain that deletion is blocked while Devices are assigned.
- Use accurate success, conflict, and retry states.

### Authentication

Login, first-run setup, and Operator acceptance use a shared split layout.

- Brand, concise product purpose, and abstract operational visual on one side.
- Focused form and contextual feedback on the other.
- No sidebar or authenticated navigation.
- Responsive single-column fallback.
- Correct loading, validation, request failure, and completion states.
- First-run status-request failure renders an actionable state rather than an
  empty card.

## Live monitoring behavior

For Admins subscribed to the dashboard stream:

- A new `alert` State produces a prominent notification and activity entry.
- A new `warning` State updates the Open Alert count and activity without a
  modal interruption.
- Recovery to `ok` creates a subtle activity confirmation.
- Stream states are `connecting`, `connected`, `reconnecting`, and `offline`.
- Keepalive activity updates transport freshness, not Device reporting time.
- The UI says **Realtime channel connected**; it never infers RabbitMQ or overall
  system health from the SSE connection.
- User-action success and failure use contextual feedback adjacent to the action
  or in a toast when appropriate.

## Data states

Every data view supports:

- branded skeletons during initial loading;
- quiet background refresh while retaining content;
- an error banner with Retry;
- stale-data labeling;
- contextual empty states;
- distinct no-filter-results states;
- accessible pending states;
- focused retry after network or server failure.

Generic “Loading…” and “No items.” text is not sufficient.

## Responsive behavior

### Desktop, 1440px and wider

- Expanded sidebar.
- Full data tables.
- Multi-column KPI and detail layouts.
- Persistent top bar.

### Laptop, 1024px

- Sidebar may start collapsed based on available width and user preference.
- Tables retain priority columns and may use controlled secondary-column hiding.
- Actions remain available without overflow.

### Tablet, below 1024px

- Sidebar becomes a drawer.
- Filters move into a sheet or stacked toolbar.
- Detail layouts become single-column.

### Mobile, 390px

- Sidebar is fully off-canvas.
- Tables become compact lists with State, identity, and key metadata first.
- Filters use a dedicated sheet.
- Primary actions remain reachable without horizontal scrolling.
- KPI strip becomes a two-column or horizontally swipeable set with clear labels.

## Accessibility

Release acceptance requires:

- WCAG AA contrast in both themes;
- complete keyboard operation;
- visible focus indicators;
- semantic landmarks and heading order;
- accessible names for icon-only controls;
- State communicated by icon, text, and color;
- reduced-motion support;
- minimum touch targets on mobile;
- dialogs that manage focus and close predictably;
- screen-reader text for compact visual State distributions.

Motion is limited to 150–200ms navigation, menu, and feedback transitions. No
decorative animation is used.

## Technical direction

- Keep Nuxt 3, Vue 3, TypeScript, Tailwind, and `@nuxt/ui`.
- Do not add a chart library or replacement component framework.
- Add semantic design tokens and global theme configuration.
- Introduce separate default and authentication layouts.
- Build shared shell, scope, page-header, status, and data-state components only
  where they remove repeated behavior or establish a shared visual contract.
- Extract Realtime stream connection state into a shared composable.
- Cache scoped Datacenter metadata in shared frontend state.
- Preserve the existing same-origin API wrapper and in-memory access-token model.
- Local storage may contain only explicit UI preferences such as theme and
  sidebar state, never authentication material.

## Implementation sequence

1. **Foundation and shell**
   - semantic tokens, theme modes, typography, logo;
   - default and authentication layouts;
   - sidebar, top bar, scope, and user menu.
2. **Overview**
   - KPI strip, attention panel, Datacenter health table, freshness states.
3. **Devices**
   - inventory toolbar, filtering, sorting, pagination, responsive rows;
   - Device detail and CRUD feedback.
4. **Alerts**
   - Open/Acknowledged tabs, shared stream state, Acknowledgment and Retry Reset.
5. **Datacenters and authentication**
   - management patterns and split authentication layout.
6. **Verification**
   - unit/component coverage where practical;
   - device and dashboard backend tests;
   - frontend typecheck and production build;
   - role/theme/viewport acceptance pass;
   - API and authorization regression checks.

## Acceptance criteria

- The product has a distinct Unplugd identity in light and dark themes.
- The authenticated shell uses the approved sidebar and role-aware navigation.
- Global, Scoped, and Operator users see correct role and Datacenter context.
- Scoped Datacenter names are securely available without exposing other
  Datacenters.
- Overview, Devices, Alerts, Datacenters, and authentication routes use the
  shared visual system.
- No view claims telemetry, uptime, broker health, or reset success unsupported
  by current data.
- All primary workflows are keyboard accessible and usable at 1440px, 1024px,
  and 390px.
- State is never communicated by color alone.
- All agreed loading, stale, empty, filtered-empty, error, and pending states are
  implemented.
- Device tests, scoped Datacenter authorization tests, dashboard tests,
  frontend typecheck, and frontend production build pass.

## Domain documentation

The UI uses the terms in `docs/glossary.md` as canonical. In particular:

- Device health uses **State**, not generic Status.
- An unacknowledged record is an **Open Alert**.
- **Acknowledgment** and Device reset are separate outcomes.
- Users are **Operator**, **Scoped Admin**, or **Global Admin**.
- **Reported by** does not imply that the actor must be an Operator.

No ADR is required for this visual direction. The choices use the existing stack,
do not introduce a surprising architectural constraint, and remain reversible
through ordinary frontend refactoring. The scoped Datacenter read is a
least-privilege authorization correction with tests, not a new domain
architecture.
