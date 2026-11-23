# Unplugd

Open-source DCIM platform that companies deploy to manage devices across their datacenters. This glossary fixes the domain vocabulary; decisions live in `docs/adr/`.

## Language

**Setup**:
The first-run flow that creates the first Admin account for a deployment. It is available only while no active Admin exists.
_Avoid_: Bootstrap, onboarding, super-admin wizard

**Admin**:
A user accountable for the whole deployment or for one Datacenter.
_Avoid_: Super admin, superadmin, super-admin, guard

**Global Admin**:
An Admin with no Datacenter assignment, able to act across every Datacenter.
_Avoid_: Super admin, root admin, owner

**Operator**:
A user scoped to exactly one Datacenter.
_Avoid_: User, tenant, guard
