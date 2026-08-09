# Authentication Operations

MockInterview v1 uses Google OIDC only. Existing pre-provisioned users bind by unique verified
email. Otherwise, an exact active email-domain mapping atomically creates an active Candidate,
profile, Google identity, provenance link, and session in the mapped organization. Browser clients
receive only an opaque application cookie and a readable CSRF token—not Google tokens or claims.

## Local and staging setup

Copy `.env.example` to `.env.local`, generate a Fernet key, configure a Google web client callback
as `/api/v1/auth/google/callback`, set `FRONTEND_APPLICATION_ORIGIN` to one allowed frontend origin,
then run PostgreSQL, Alembic upgrade, and `seed_auth.py`. The fake
provider is test-only and production settings reject it. Staging uses separate non-production
Google credentials and never records callback codes, tokens, or raw claims.

## Lifecycle operations

- Migrate with `.venv/bin/python -m alembic -c apps/api/alembic.ini upgrade head`; use a new forward
  migration for production recovery. Downgrade is isolated pre-release validation only.
- Seed idempotently with `.venv/bin/python apps/api/scripts/seed_auth.py --env-file .env.local`.
- Seed an approved development domain with `--domain-mapping example.com:organization-slug`.
- Revision `002` introduces provenance-preserving soft removal. Revisions `003` and `004` create
  the active `ideas2it` organization and its `ideas2it.com` registration mapping. Never edit
  revision `001`; use a forward corrective migration for production recovery.
- Admin mapping APIs list/create/reassign/remove under
  `/api/v1/admin/organization-domain-mappings`. Mutations require an Admin session, exact Origin,
  and matching CSRF token. Removal disables only provenance-linked Candidates. Reassignment moves
  all registered PostgreSQL participants atomically; any collision or participant failure rolls
  back the mapping, Candidate data, session revocation, and new audit events.
- Remove expired transient state with `.venv/bin/python apps/api/scripts/cleanup_auth_state.py`.
- Global revocation is `POST /api/v1/auth/logout` with exact Origin and CSRF evidence. Admin role or
  disable mutations revoke all sessions in the same database transaction.
- Rotate PKCE encryption keys by listing the new key first and retaining the previous key until the
  maximum OAuth transaction TTL has elapsed; then remove the old key.

## Incident response

For suspected session theft, disable the user or perform a security revocation, verify every live
session row is revoked, and inspect correlated safe audit events. Rotate application/OIDC secrets
through the secret manager and redeploy. Never paste cookies, authorization codes, state, nonce,
Google subjects/emails, or raw claims into tickets or logs. Metrics use bounded reason/role labels;
audit metadata accepts only an explicit safe allowlist.

For a domain-mapping incident, first stop the Admin mutation, retain the soft-removed provenance
row, inspect correlation-linked safe audit events, and correct the issue with a new transaction or
forward migration. Never repair tenant ownership with ad-hoc SQL, rewrite historical AuditEvents,
or retry a reassignment until target-email and participant preflight failures are resolved.
