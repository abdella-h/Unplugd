# ADR-0001: Roles and account-creation model

**Status:** Accepted
**Date:** 2026-08-08

## Context

Open-source DCIM platform, deployed by third-party companies (multi-datacenter). In the previous implementation, a single bootstrapped admin created all other admins and operators. The failure mode that matters most (recorded during the grilling session): a rogue admin mass-creating other admins. In a flat peer group this cannot be structurally prevented — the worst admin act (self-replication of the admin role) has no in-system guardrail.

## Decision

Ship a **two-role, structurally contained** model:

1. **Roles: `admin` and `operator`.** No "super-admin" tier in the data model. The first admin is provisioned either out-of-band (deployer CLI/script) or through the one-time first-run setup endpoint while no active admin exists.

2. **Account-creation matrix:**
   - `admin` can create/remove `operator` accounts, and assign/change their `datacenter_id`.
   - Creating `admin` accounts is NOT available through the API by default. It is done out-of-band by the company that deploys the platform.
   - Optional escape hatch: config flag `ALLOW_ADMIN_CREATE_ADMIN=true` lets an org re-enable admin-creates-admin through the API for companies that accept flat propagation. Disabled by default.

3. **Consequence:** a rogue admin (compromised or malicious) can at worst mass-create operators — a bounded blast radius. The admin tier cannot grow explosively through the web API, and admin provisioning is limited to the documented out-of-band mechanism.

4. **Bootstrapped admin security floor:** if the seed provisions an initial admin, the seeded known credential logs a `must_change_password` state in the users table and the app forces a password change on first login. Known credentials in an open repo are not acceptable otherwise.

## Consequences

- Simple mental model (two roles) for UI, docs, and adopting orgs.
- Primary risk contains all structural users.
- Acceptable trade-off: an org with no out-of-band CLI access cannot invite a second admin through the UI until it decides to allow it (`ALLOW_ADMIN_CREATE_ADMIN`) — a deliberate, documented choice per org.
- The unauthenticated first-run setup path is available only until the first active Admin exists; deployments that prohibit it can use the out-of-band provisioning path instead.
- Role vocabulary is now consistent: `admin` / `operator`. The previous `guard`/`user` terminology is dropped.