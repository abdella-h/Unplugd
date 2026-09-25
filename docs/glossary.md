# Glossary

Domain vocabulary for the DC monitor platform. Terms are final as recorded;
if a term changes meaning, update the glossary before touching code.

| Term | Definition |
|------|------------|
| Datacenter | A physical facility monitored by the platform. The unit of scoping/canvas. A company may operate many datacenters. |
| Device | A non-smart physical asset inside a datacenter (cable, cooling system, etc.) that has no telemetry of its own. Human observation is the only sensor. |
| State | The human-reported health status of a device, from the enum `ok` / `warning` / `alert` (lowercase; stored and compared exactly). |
| Operator | Field personnel who physically enter a datacenter and report the state of each Device. Human-in-the-loop is the system's core: Devices have no self-reporting. |
| Admin | Company employee who watches the dashboard and acts on Device States reported by Operators, including acknowledging Alerts. An Admin is not a field reporter, but may use approved State-reporting controls. |
| User Profile | A read-only presentation of the authenticated user's own account identity and access metadata; it is not a separate account or a user directory. |
| Alert | A dashboard record raised when a Device enters `warning` / `alert` State. |
| Open Alert | An Alert that has not been acknowledged by an Admin. |
| Acknowledgment | The admin action that marks an Alert as acknowledged and attempts to reset the Device to `ok`. The acknowledgment can succeed even when the reset fails. |
| Bootstrap Admin | The first Global Admin, provisioned during deployment or first-run setup before any active Admin exists. |
| Account Creation | A privileged action: an `admin` creates `operator` accounts inside the platform. Admin accounts are created out-of-band (deployer CLI/script) or via opt-in flag `ALLOW_ADMIN_CREATE_ADMIN`. Self-registration is not intended. |
| Operator Scoping | An operator is bound to exactly one datacenter (`datacenter_id` mandatory) and can neither see nor report on devices in other datacenters. |
| Admin Scoping | An admin with `datacenter_id` null is global (sees + acknowledges all DCs); an admin with `datacenter_id` set is scoped to one datacenter only. |
| Multi-Datacenter | The platform is designed for companies with more than one datacenter; account creation, alerting, and scoping all assume this. |
| Access Token | A signed JWT issued by `/login` on successful authentication. Claims: `sub` (username), `role` (`admin`/`operator`), `dc_id` (datacenter id or null), `exp` (15m). It is the credential downstream services trust for scoping per ADR-0002. |
| Session | A logged-in state represented server-side by a live Refresh Token (ADR-0004) plus the short-lived Access Tokens it mints. |
| Refresh Token | An opaque random string (never a JWT) issued at `/login` and rotated at each `/refresh`. Stored only as a SHA-256 hash in `refresh_tokens`. Transported in an HttpOnly cookie. Lifetime 7 days, absolute. See ADR-0004. |
| Token Family | *Deferred* — all refresh tokens descending from one `/login` sharing a `family_id`, enabling lineage-wide revocation. Not implemented in the first cut; see ADR-0004 §2. |
| Rotation | The act of issuing a fresh Refresh Token on every `/refresh` while marking the presented one consumed (`rotated_at`). The legitimate client always holds exactly the newest token. |
| Reuse Detection | *Deferred (no containment in this iteration)* — presenting a consumed token currently returns `401` only; no cascade revocation. Family-wide revocation is deferred with `family_id`. See ADR-0004 §2. |
| Lockout | A defensive state where a user account is temporarily refused login after N consecutive failed attempts (tracked by `failed_login_count` + `locked_until`, ADR-0003). Complements gateway-level rate limiting. |
| Failed Login Attempt | A login that did not issue a token (bad credentials, inactive account, or invalid role). Counted per user to drive Lockout. |