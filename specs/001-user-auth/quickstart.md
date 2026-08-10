# Quickstart Validation: User Authentication and Role Access

> The domain-mapped Candidate registration implementation passed its automated validation on
> 2026-08-09. Manual screen-reader and staging-provider evidence remain separately identified in
> `validation.md` and are not represented as automated passes.

This guide defines the runnable evidence expected after implementation. Regenerated tasks must
create the referenced manifests/scripts with these stable command interfaces.

## Prerequisites

- Python 3.12 environment for `apps/api`.
- Node.js environment supported by the generated `apps/web/package.json`.
- Docker/Compose or another local PostgreSQL instance.
- Non-production Google OIDC configuration for a separately marked staging smoke test.
- Deterministic fake OIDC configuration enabled only in tests; production configuration must reject it.
- Developer-controlled Candidate, Manager, and Admin emails supplied through environment/seed
  input, never embedded as production identities.

## Setup and Static Gates

First verify version control; stop for repository-owner action if this fails:

```bash
git rev-parse --git-dir
```

Then run:

```bash
cp .env.example .env.local
python3.12 -m venv .venv
.venv/bin/python -m pip install -e 'apps/api[dev]'
npm ci --prefix apps/web
docker compose up -d postgres
.venv/bin/python -m alembic -c apps/api/alembic.ini upgrade head
.venv/bin/python apps/api/scripts/seed_auth.py --env-file .env.local \
  --domain-mapping example.test:mockinterview-development
.venv/bin/python apps/api/scripts/seed_auth.py --env-file .env.local \
  --domain-mapping example.test:mockinterview-development
.venv/bin/ruff check apps/api
.venv/bin/python -m mypy --config-file apps/api/pyproject.toml apps/api/app
npm --prefix apps/web run lint
npm --prefix apps/web run typecheck
```

Expected:

- Missing or unsafe production cookie/OIDC/session configuration fails startup safely.
- Missing or invalid `OAUTH_TRANSACTION_ENCRYPTION_KEYS` fails startup; current and previous key
  rotation values decrypt only their intended short-lived PKCE records.
- The fake OIDC adapter cannot be selected in production mode.
- No migration or seed contains a real production identity or secret.

## Scenario 1: Migration and Constraint Recovery

Run the PostgreSQL migration suite:

```bash
.venv/bin/pytest -c apps/api/pyproject.toml apps/api/tests/integration/test_auth_schema.py
```

1. Populate revision `001`, upgrade `001` → `002`, and verify existing Users have null registration
   provenance and unchanged authorization state.
2. Verify every named uniqueness, tenancy, role/status, identity, Candidate-link, and token-digest
   constraint.
3. Downgrade head → base in an isolated database.
4. Upgrade base → head again.
5. Exercise active-domain uniqueness, provenance, normalized-email, `(issuer, subject)`,
   User/provider, CandidateProfile, session digest, and `ON UPDATE CASCADE` tenant constraints.

Expected: migrations round-trip in the test environment; every collision fails atomically without
partial User, identity, profile, session, or audit state.

## Scenario 2: First Google Binding, Registration, and Role Login

Using the deterministic OIDC fake:

1. Pre-provision one active User for each role using domains with no organization mapping.
2. Give the Candidate its one-to-one CandidateProfile.
3. Complete a first login for each using verified email and a stable fake issuer/subject.
4. Complete a second login with the same subjects.
5. Change the provider email while retaining the same subject and log in again.
6. Sign in a new identity with an exact active domain mapping and a valid signed Google name.
7. Repeat with no usable name and verify the validated email local-part fallback.
8. Pre-provision one unbound User whose email domain maps to a different organization, then complete
   first login with that exact email.

Expected:

- First login atomically binds one subject to the existing User; it creates no User, role, org, or
  profile and does not require or add a domain-mapping provenance link.
- A new mapped identity atomically creates exactly one active Candidate User, CandidateProfile,
  ExternalLoginIdentity, registration provenance link, session, and required audit events.
- When pre-provisioned binding and domain mapping both apply, the existing unique User wins before
  mapping lookup, binds in its original organization, and retains null registration provenance;
  no Candidate is created or diverted into the mapped organization.
- Later logins resolve by subject, including after email drift.
- Candidate lands at allocated-interviews shell/empty state; Manager at JD/allocation workspace;
  Admin at application management.
- `/api/v1/auth/me` returns only the role-discriminated contract and session expiries.

## Scenario 3: Login Denials and Recovery

Exercise cancelled login, expired/replayed state, nonce mismatch, wrong issuer/audience, invalid
signature, expired claims, missing subject/email, unverified email, provider unavailability,
unprovisioned email, disabled User, duplicate subject, ambiguous binding, and profile conflict.

Expected:

- No application session is created.
- Browser-visible errors contain only a safe enum, approved recovery action, and correlation ID.
- Expired/logged-out directs sign-in; unprovisioned/disabled directs contact Admin; provider errors
  direct retry.
- Audit/log output contains no token, cookie, authorization code, state, nonce, or raw claims.

## Scenario 4: Permission and Isolation Matrix

Use test-only protected routers/resources implementing [access-policy.md](./contracts/access-policy.md):

1. Candidate own and other-Candidate resources in the same organization.
2. Candidate cross-organization resource.
3. Manager managed and another Manager's readiness resource.
4. Manager all-report/Admin-management attempts.
5. Admin application management and report capabilities.
6. Every policy with missing required ResourceScope fields.

Expected: every allowed matrix combination succeeds; every denied combination returns the
documented safe 403/non-enumerating 404 without protected content and emits an audit event.

## Scenario 5: Global Logout Across Devices

1. Create two active sessions for the same User in two browser contexts.
2. Confirm both can request `/auth/me` and one allowed protected fixture.
3. POST logout with valid CSRF and Origin evidence from one context.
4. Retry protected requests from both contexts and use browser back/history navigation.
5. Repeat logout with missing/expired and already-revoked cookies.

Expected:

- Recognizable logout increments User auth generation and revokes every session.
- Both contexts are denied afterward; protected client state is cleared and history reveals no
  protected response.
- Repeated/unrecognizable logout clears the local cookie and remains successful.
- Invalid CSRF/origin evidence is denied without revocation.

## Scenario 6: Role Change, Disablement, and Re-enable

For a User with two sessions:

1. Change the role through the Admin contract.
2. Verify both sessions fail and a new login receives the new role.
3. Disable the User; verify all new/current access fails with contact-Admin recovery.
4. Re-enable the User; verify old sessions remain invalid and a new login is required.
5. Change a User to Candidate and verify the profile is created/validated atomically.
6. Attempt to change a Candidate with a profile to Manager/Admin.

Expected: mutation, generation increment, session revocation, Candidate invariant, and audit event
commit together or roll back together. The Candidate→non-Candidate request returns
`CANDIDATE_PROFILE_CONFLICT` and leaves role, generation, profile, sessions, and audit state
unchanged; profile lifecycle is not inferred by this feature.

## Scenario 7: Absolute and Idle Expiry

Use an injected controllable clock:

1. Create a session and advance just before/at/after two-hour idle expiry.
2. Make an authenticated request before idle expiry and verify extension does not exceed absolute
   expiry.
3. Advance just before/at/after eight-hour absolute expiry.

Expected: boundary behavior is deterministic; ended sessions never succeed in a later protected
request and receive sign-in recovery.

## Scenario 8: Cookie, Cache, and Browser Exposure

Inspect login callback, `/auth/me`, protected identity, and logout responses.

Expected in production mode:

- Cookie is `__Host-mi_session; Secure; HttpOnly; SameSite=Lax; Path=/` with no Domain.
- A separate readable `mi_csrf` cookie is Secure outside local development, SameSite=Lax, Path=/,
  has no Domain, matches `X-CSRF-Token`, and matches the digest bound to the server-side session.
- `Cache-Control: no-store` is present.
- Session/OAuth tokens, subject, email snapshot, and internal audit/session identifiers are absent
  from browser-visible bodies and storage.
- CORS uses exact configured origins with credentials; wildcard origin is absent.

## Scenario 9: Google-Only Surface

Inspect generated OpenAPI and every authentication view/route.

Expected: no password login, creation, change, forgotten-password, recovery, reset, expiry, lockout,
or public registration endpoint/control exists.

## Scenario 10: Accessibility

Run component semantics/keyboard tests and Playwright axe checks for login, every safe error
category, protected loading/forbidden state, each role landing view, and session expiry. Complete
the documented manual keyboard and NVDA or VoiceOver pass.

Expected:

- Zero automated WCAG 2.2 AA violations.
- All controls work by keyboard with visible focus and logical order.
- Route changes focus the page heading.
- Blocking errors announce through `role="alert"`; statuses use a polite live region.
- Recovery does not rely on color; tested contrast passes in normal/focus/error states.

## Scenario 11: Audit and Secret Safety

Generate login success/denial, identity binding/collision, logout-all, expiry, role/status mutation,
session revocation, Candidate-link collision, and authorization denial.

Expected: each produces the required immutable AuditEvent and correlated structured log with safe
reason codes. Run a secret scan over source, fixtures, logs, audit metadata, browser bundles, and
test artifacts; it must find no credential or reusable token.

## Scenario 12: Coverage and Full Test Gates

Run the root enforcement command:

```bash
bash scripts/quality-gate.sh
```

It invokes:

- backend unit, contract, PostgreSQL integration, migration, lint, type, and coverage suites;
- frontend unit, strict type, lint, and 100% line/branch/function/statement coverage suites;
- Playwright critical authentication journeys.

Expected: `.coverage-thresholds.json` explicitly describes both backend and frontend enforcement;
all configured metrics meet 100%, and no task/PR completion bypasses the gate.

## Scenario 13: Non-Blocking Performance Baseline

Run the representative PostgreSQL-backed baseline:

```bash
.venv/bin/python apps/api/scripts/auth_baseline.py \
  --warmup-seconds 10 \
  --duration-seconds 60 \
  --concurrency 20 \
  --seeded-sessions 100 \
  --mix auth-me=50,allowed=15,denied=15,known-login=10,mapped-first-login=10 \
  --output specs/001-user-auth/performance/baseline.json
```

The request mix exercises `/auth/me`, allowed and denied policy requests, known subject login, and
mapped Candidate first login.

Expected artifacts record build identifier, environment/database configuration, request mix,
sustained requests/second, p50, p95, and expected/unexpected status counts. Correctness or setup
failure fails the command; numeric throughput/latency does not.

## CI and Pre-Push Integration

Verify the existing consumers call the same root gate:

```bash
rg -n 'scripts/quality-gate.sh' .coverage-thresholds.json .github/workflows/ci.yml .husky/pre-push
```

Expected:

- `.coverage-thresholds.json` declares backend and frontend suites and uses
  `bash scripts/quality-gate.sh` as the blocking command.
- `.github/workflows/ci.yml` configures Python, Node, and PostgreSQL, installs both projects, and
  invokes the script.
- `.husky/pre-push` invokes the script directly and does not evaluate a configuration string.

## Scenario 14: Named Security and Privacy Review

Review OIDC CSRF/nonce/PKCE, callback replay, configured frontend redirects, exact/IDNA domain
validation, advisory-lock namespace/order, registration collision, mapping Admin authorization,
tenant migration/rollback, participant completeness, session fixation/theft, cookie/CORS/CSRF,
login abuse/rate limiting, trusted proxies, account enumeration, audit privacy, secret handling,
global revocation, cache/history, and development/test adapter isolation.

Expected: zero unresolved critical or high-severity issue before release. Any accepted lower issue
has an owner and remediation date.

## Scenario 15: Exact Domain Registration Denials

Exercise case-insensitive exact matches plus unmapped, removed, disabled-organization, malformed,
wildcard, URL-shaped, `@`-containing, parent-domain, and subdomain inputs.

Expected: only the exact canonical active mapping registers. Every denial returns safe recovery and
leaves zero partial User, profile, identity, session, provenance, or success-audit rows.

## Scenario 16: Admin Mapping API and Audit

Exercise list/create/reassign/remove as Admin and repeat every operation with missing authentication,
Candidate/Manager sessions, missing/invalid CSRF, duplicate active domain, missing/disabled target
organization, removed mapping, and malformed payload. From an allowed frontend origin, issue a CORS
preflight for `DELETE /api/v1/admin/organization-domain-mappings/{mapping_id}` and repeat it from a
disallowed origin.

Expected: only authorized Admin operations succeed. Mutations and denials emit safe audit evidence;
responses and logs contain no email, display name, domain, Google claim, or credential beyond the
explicit Admin mapping response contract. The allowed-origin DELETE preflight succeeds with
credentialed exact-origin headers; the disallowed-origin preflight is denied.

## Scenario 17: Mapping Removal

Create active and disabled self-registered Candidates through one mapping, an independently
pre-provisioned same-domain Candidate, unrelated mapping users, and multiple active sessions.
Remove the mapping twice.

Expected: the first removal soft-removes the mapping, disables exactly provenance-linked
Candidates, increments their generations, revokes every active session with
`DOMAIN_MAPPING_REMOVED`, and preserves all unrelated/pre-provisioned users. Replay follows the
documented not-found/conflict contract and makes no additional mutation.

## Scenario 18: Atomic Mapping Reassignment

Reassign a populated mapping to an active organization. Include authentication rows and a synthetic
Candidate-owned tenant-migration participant. Repeat with a target email collision, disabled target,
participant validation failure, participant write failure, audit failure, and a target organization
equal to the current mapping organization.

Expected: success migrates mapping, provenance-linked Users, profiles, identities, sessions, and
participant rows; increments generations; revokes sessions with `DOMAIN_MAPPING_REASSIGNED`; and
requires fresh login in the target organization. Every injected failure leaves all source rows,
mapping state, generations, sessions, and audit counts unchanged. Historical AuditEvents remain in
their original organization. A same-organization request returns `200` with the current mapping and
does not invoke participants, change generations, revoke sessions, or append mutation audits.

## Scenario 19: Registration and Mapping Concurrency

Use two independent PostgreSQL sessions and deterministic barriers/timeouts for registration racing
mapping create, removal, and reassignment in both lock orders. Repeat concurrent callbacks for one
new Google subject.

Expected: advisory-domain then row-lock ordering produces one complete pre- or post-mutation state,
never a mixed tenant. Duplicate callbacks create one User/identity only. Tests fail on deadlock or
timeout rather than hanging.

## Scenario 20: Frontend Callback Redirects

Exercise success and every safe callback failure with hostile Host/Forwarded headers.

Expected: redirects use only the validated configured frontend application origin and allowlisted
relative path. Error redirects contain only an allowlisted code and opaque correlation ID; the web
route announces safe recovery accessibly and never lands on the API server's `/auth/error` path.

## Staging-Only Google Smoke Test

Run separately from routine CI using approved non-production credentials. Verify discovery,
authorization redirect, callback, and stable subject binding. Do not record tokens or claims in
test output. A staging-provider failure does not replace deterministic CI evidence.
