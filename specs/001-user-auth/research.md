# Research: User Authentication and Role Access

## Decision 1: Backend-managed Google OpenID Connect

**Decision**: Use the OpenID Connect Authorization Code flow with PKCE through a narrow Authlib
adapter. Store a short-lived, one-time OAuth transaction containing hashed state/nonce lookup data,
PKCE verifier encrypted with Cryptography Fernet/MultiFernet, an allowlisted return target, expiry,
and consumption time. Encryption keys come from a validated `OAUTH_TRANSACTION_ENCRYPTION_KEYS`
environment setting supporting current and previous rotation keys. Validate issuer,
audience, signature, expiry, nonce, `sub`, email, and `email_verified`. Request only `openid email
profile`. Never expose or retain Google access, refresh, or ID tokens after the callback.

**Rationale**: The backend must verify identity and keep provider credentials out of browser
JavaScript. Google documents `sub` as the stable identifier; state, nonce, and PKCE bind the
callback to the initiating browser transaction.

**Alternatives considered**:

- Hand-written token/JWK verification: rejected due to cryptographic maintenance risk.
- SPA token or implicit flow: rejected because reusable credentials reach JavaScript.
- Email as the durable identity key: rejected because email can change.

**References**: [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect),
[OAuth 2.0 Security BCP](https://datatracker.ietf.org/doc/html/rfc9700),
[Authlib Starlette integration](https://docs.authlib.org/en/v1.7.0/oauth2/client/web/starlette.html)

## Decision 2: First-login binding for pre-provisioned users

**Decision**: Admin provisioning creates the User, organization, role, status, and Candidate-profile
association before login. On the first successful Google callback, atomically match the verified
normalized email to exactly one active, unbound User in the single v1 organization and bind
`(issuer, subject)` to it. Do not create an account or authorization state during login. Subsequent
logins resolve only by `(issuer, subject)`; email drift never rebinds automatically. Collision or
ambiguity is denied and audited. Explicit identity rebinding is not part of v1.

**Rationale**: Admins typically cannot know a Google subject before first login. This preserves the
pre-provisioning requirement while making the clarified stable-subject association operational.
V1 is single-organization; future multi-tenant login will need an organization hint or invitation
context if the same normalized email can exist in multiple organizations.

**Alternatives considered**:

- Admin supplies Google `sub`: secure but operationally impractical for normal provisioning.
- Match email on every login: rejected because it silently moves identity.
- Create the User during callback: rejected by FR-001.

## Decision 3: Typed PostgreSQL persistence

**Decision**: Use SQLAlchemy 2 typed declarative models, one `AsyncSession` per request/task,
psycopg 3, and Alembic. Use UUID primary keys, timezone-aware timestamps, named constraints, string
role/status values with database checks, organization-scoped uniqueness, and composite tenancy
constraints where relationships cross owned records.

**Rationale**: PostgreSQL is the system of record and can enforce uniqueness under concurrent
callbacks. SQLAlchemy documents `AsyncSession` as stateful and not safe to share between concurrent
tasks, so request-scoped transactions are explicit.

**Alternatives considered**:

- SQLite integration tests: rejected because they do not prove PostgreSQL constraints or migration behavior.
- Native PostgreSQL enums: viable, but checked strings simplify forward and downgrade migrations.
- `create_all()` schema management: rejected because every relational change requires a migration.

**Reference**: [SQLAlchemy session concurrency](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)

## Decision 4: PostgreSQL-backed opaque application sessions

**Decision**: Generate at least 256 bits of random session secret, send it only in a cookie, and
store only its SHA-256 digest. Each session records user/organization, auth generation, creation,
last activity, absolute and idle expiries, and revocation metadata. Creation sets an 8-hour
absolute expiry and a 2-hour idle expiry. Each authenticated request validates both expiries,
active User status, organization consistency, revocation, and auth-generation equality, then
updates the idle expiry to `min(now + 2 hours, absolute expiry)`. V1 has no concurrent-session
limit.

**Rationale**: Opaque server-side sessions support immediate global invalidation without stale
browser claims or a JWT denylist. PostgreSQL avoids a new Redis dependency and permits session,
User mutation, revocation, and audit changes in one transaction.

**Alternatives considered**:

- JWT cookie: rejected because immediate global invalidation still needs server state.
- Redis-only sessions: rejected because v1 already requires PostgreSQL and transactional audit history.
- Raw token storage: rejected because a database read would disclose active credentials.
- Touch throttling: deferred because it weakens the exact idle policy.

## Decision 5: Global invalidation generation

**Decision**: Maintain `User.auth_generation`. Logout from a recognizable session, role change, or
disablement increments the generation, revokes every active session row with a safe reason, and
writes an AuditEvent in one transaction. Re-enabling never restores old sessions. Logout is
idempotent: when no retained session identifies a user, clear the local cookie and return success;
when it does, revoke every session for that user.

**Rationale**: Generation comparison provides constant-time invalidation even if cleanup or a bulk
row update is delayed, while retained revoked rows preserve security history.

**Alternatives considered**:

- Delete session rows: rejected because it discards revocation evidence.
- Bulk update without generation: viable but weaker against missed rows.
- Re-read role without revocation: rejected by FR-010.

## Decision 6: Cookie, CSRF, cache, and redirect controls

**Decision**: In production use a `__Host-mi_session` cookie with `Secure`, `HttpOnly`,
`SameSite=Lax`, `Path=/`, and no `Domain`; use an explicitly different development cookie on local
HTTP. Generate a separate high-entropy CSRF token per application session, store only its digest,
and set the raw value in a readable `mi_csrf` cookie with `Secure` outside local development,
`SameSite=Lax`, `Path=/`, and no `Domain`. The frontend copies this cookie to `X-CSRF-Token`.
Mutating requests require exact Origin validation plus a constant-time header digest comparison.
Logout clears both cookies. Allow credentialed CORS only for configured exact frontend origins.
Return `Cache-Control: no-store` on authentication and protected identity responses. Allow only
fixed or allowlisted relative return paths.

**Rationale**: `SameSite=Lax` supports the external OIDC navigation but is defense-in-depth rather
than the only CSRF control. Host-only, secret-free opaque cookies reduce cross-subdomain and XSS
exposure.

**Alternatives considered**:

- `SameSite=Strict`: safer in isolation but can disrupt external top-level login return flows.
- `SameSite=None`: unnecessary and expands cross-site exposure.
- Cookie-only CSRF protection: rejected for global state-changing actions.
- Returning CSRF only once in a redirect/body: rejected because reload/bootstrap needs a stable
  acquisition path; the readable non-authentication cookie supplies it without exposing the
  HTTP-only session credential.

**References**: [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html),
[OWASP CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)

## Decision 7: Deny-by-default authorization contract

**Decision**: Resolve a typed immutable `AuthContext`, then apply capability, organization, and
resource-scope policies. Candidate queries scope by Candidate User/Profile ownership. Manager
readiness queries scope by organization and managing Manager. Admin capabilities are explicit, not
wildcard route bypasses. Missing and unauthorized cross-scope resources use safe non-enumerating
responses where applicable. Prove FastAPI integration with test-only routers; do not invent
production JD/report endpoints.

**Rationale**: Role checks alone cannot enforce Candidate ownership or Manager managed-interview
scope. Query-level resource scoping prevents post-fetch disclosure while respecting the feature's
domain-behavior boundary.

**Alternatives considered**:

- UI route hiding: rejected as a security control.
- Role-only decorators: rejected because ownership and organization remain unchecked.
- PostgreSQL row-level security: deferred until broader domain tables exist.

## Decision 8: Admin provisioning and Candidate invariants

**Decision**: Provide Admin-only API operations to create pre-provisioned Users and to change role
or status. Candidate creation/role assignment and CandidateProfile association occur in one
transaction before a Candidate becomes active. Database uniqueness enforces at most one profile
per User and one User per profile; services enforce the "every Candidate has exactly one profile"
and same-organization invariant because a simple foreign key cannot enforce the role-conditional
existence rule. V1 rejects a role change from Candidate to Manager/Admin with
`CANDIDATE_PROFILE_CONFLICT` while a CandidateProfile exists; profile archival/deletion requires a
separately specified Candidate lifecycle and is not inferred by authentication. Successful
role/status mutations revoke all sessions and audit atomically.

**Rationale**: Seed data alone does not satisfy FR-001, and role/disable revocation cannot be tested
without an authoritative mutation path.

**Alternatives considered**:

- Deferred constraint trigger: rejected initially due to complexity and migration burden.
- Candidate profile creation on login: rejected because login cannot provision authorization state.

## Decision 9: Audit and observability

**Decision**: Persist append-only AuditEvents for login success/denial, logout-all, expiry,
revocation, provisioning, enable/disable, role change, identity/profile collision, and authorization
denial. Store known actor/target/org identifiers, outcome, safe reason code, resource reference,
correlation ID, timestamp, and allowlisted metadata. Actor/org may be null for unknown identities.
Never store tokens, cookies, authorization codes, raw state/nonce, or unprovisioned identity claims.
Emit structured logs and counters using the same correlation and reason codes.

**Rationale**: Durable events support investigation; logs provide operational visibility. Security-
sensitive successful mutations fail closed if their audit write cannot commit.

**Alternatives considered**:

- Logs only: rejected due to weaker retention/query guarantees.
- Full claims/request capture: rejected as unnecessary personal and secret data.

## Decision 10: Frontend authentication module

**Decision**: Use a small `apps/web/src/auth` module with a discriminated state union for loading,
anonymous, authenticated, and safe error states. Fetch with credentials, decode network payloads
from `unknown`, and map roles/errors exhaustively. Candidate current-user context requires
`candidateProfileId`; Manager/Admin variants do not. Keep role navigation as UX only. Clear all
protected client state whenever authentication is lost.

**Rationale**: Exhaustive local state is sufficient for the initial auth surface and avoids a
global state dependency. Runtime decoding remains necessary even with generated TypeScript types.

**Alternatives considered**:

- Redux or a state-machine library: deferred until broader application state justifies it.
- Zod solely for the initial auth response: rejected; narrow handwritten decoders are sufficient.
- Browser token storage: rejected because no reusable credential should reach JavaScript.

## Decision 11: Stable error and accessibility contracts

**Decision**: Return a safe error envelope with fixed error/recovery enums and a correlation ID.
Map expired/revoked sessions to sign-in, unprovisioned/disabled accounts to contact Admin,
provider/callback failures to retry, and authorization denial to the role home. OAuth failures
redirect with only a safe enum and correlation ID. Authentication views use semantic controls,
visible focus, heading focus on route changes, alert/status live regions, non-color recovery copy,
and WCAG 2.2 AA contrast. Verify with component semantics, Playwright axe checks, and documented
manual keyboard plus NVDA/VoiceOver checks.

**Rationale**: The clarified spec requires actionable recovery without account disclosure and both
automated and manual accessibility evidence.

## Decision 12: Layered testing and coverage source of truth

**Decision**: Use pytest, pytest-asyncio, HTTPX, PostgreSQL, Alembic migration tests, controllable
clocks, and deterministic OIDC fakes for the backend; Vitest/Testing Library for frontend units;
Playwright for integrated journeys. Keep real Google smoke tests separately marked for staging.
Revise `.coverage-thresholds.json` before implementation so it explicitly defines frontend and
backend commands/metrics while retaining 100% lines, branches, functions, and statements wherever
the tool exposes them; provide `scripts/quality-gate.sh` as one root enforcement command. Update
`.github/workflows/ci.yml` to install Python and Node dependencies, start PostgreSQL, and call that
script. Update `.husky/pre-push` to call the same script directly without `eval`.

**Rationale**: The current file runs only Vitest and cannot truthfully gate Python. PostgreSQL and
deterministic provider tests validate the real boundaries without flaky external CI.

**Alternatives considered**:

- Live Google in routine CI: rejected as secret-dependent and nondeterministic.
- SQLite backend integration tests: rejected due to dialect and transaction differences.
- Claiming the current Vitest command covers Python: rejected as false evidence.

## Decision 13: Non-blocking performance baseline

**Decision**: Run a repeatable PostgreSQL-backed baseline against `/auth/me`, one allowed policy
request, one denied policy request, and session idle refresh. After a 10-second warm-up, run for 60
seconds at concurrency 20 with a fixed mix of 60% `/auth/me`, 20% allowed policy request, and 20%
denied policy request against 100 seeded active sessions. Record build/environment, request mix,
sustained requests/second, p50, p95, and response correctness. Fail only for setup or correctness
errors, never for missing a numeric performance target.

**Rationale**: This satisfies SC-009 without reintroducing the rejected 1000 requests/second or
200 ms p95 gates or benchmarking Google availability.

## Dependency Review

License compatibility is evaluated from upstream SPDX declarations and must be rechecked against
the generated lockfiles before implementation dependency installation. MIT, BSD-3-Clause,
Apache-2.0, dual Apache/BSD, and LGPL-3.0 library use are compatible with this application plan;
no dependency requires distributing proprietary application source. Required notices/licenses are
retained in deployment artifacts where applicable.

| Dependency | SPDX license | Need | Maintenance/security scope | Runtime impact |
|---|---|---|---|---|
| FastAPI/Starlette | MIT / BSD-3-Clause | Constitution-selected HTTP boundary | Established project standard; validate untrusted inputs | API runtime |
| SQLAlchemy 2 + Alembic + psycopg 3 | MIT / MIT / LGPL-3.0 | Typed PostgreSQL access and migrations | One ORM/driver/migration stack | API runtime and migration tooling |
| Authlib | BSD-3-Clause | Maintained OAuth/OIDC discovery, exchange, and claim verification | Avoids custom cryptography | Login/callback only |
| Cryptography | Apache-2.0 OR BSD-3-Clause | Encrypt transient PKCE verifier at rest with rotation support | Narrow reviewed primitive; keys remain environment-only | OAuth transaction only |
| Pydantic Settings | MIT | Typed environment validation | Reuses FastAPI/Pydantic ecosystem | Startup only |
| Uvicorn | BSD-3-Clause | ASGI runtime | Single server runtime | API runtime |
| React + React Router | MIT / MIT | Constitution-selected web UI and protected routing | One UI/router stack | Browser bundle |
| Vitest + Testing Library + Playwright | MIT / MIT / Apache-2.0 | Required layered frontend/browser tests | Test-only | No production impact |
| pytest + pytest-asyncio + pytest-cov + HTTPX | MIT / Apache-2.0 / MIT / BSD-3-Clause | Required backend unit/integration/coverage | Test-only | No production impact |

Redis, JWT/session frameworks, duplicate validation/state libraries, and a new authentication
microservice are not justified for v1.
