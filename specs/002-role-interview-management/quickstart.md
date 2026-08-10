# Quickstart Validation: Role-Based Interview Management

This guide defines the runnable evidence expected after implementation. Run destructive migration
and integration checks only against an isolated PostgreSQL database, never the local database used
by the running application.

## Prerequisites

- Python 3.12 virtual environment created at `.venv`
- Node.js 22–24 and `apps/web` dependencies installed
- PostgreSQL 17 reachable through a dedicated test `DATABASE_URL`
- Backend dependencies installed from the updated `apps/api/requirements.lock`
- Current feature contract at `specs/002-role-interview-management/contracts/role-interview.openapi.yaml`
- Google provider fakes for deterministic tests; real credentials are only for a separately marked
  staging smoke test

## Setup

From the repository root:

```bash
.venv/bin/python -m pip install --requirement apps/api/requirements.lock
.venv/bin/python -m pip install --no-deps --editable apps/api
npm ci --prefix apps/web
npx --prefix apps/web playwright install --with-deps chromium
```

Set both runtime and migration URLs to the same isolated test database, then apply migrations.
Alembic prefers the explicit migration URL over its checked-in configuration fallback:

```bash
export DATABASE_URL='postgresql+psycopg://.../isolated_test_database'
export MOCKINTERVIEW_MIGRATION_DATABASE_URL="$DATABASE_URL"
.venv/bin/python -m alembic -c apps/api/alembic.ini upgrade head
.venv/bin/python -m alembic -c apps/api/alembic.ini current
```

Expected: current revision is `005`; existing revision `004` auth, mapping, session, and audit data
remain intact; `profile_picture_url`, `job_descriptions`, and `scheduled_interviews` exist with the
named constraints and indexes in [data-model.md](data-model.md).

## Focused backend validation

Run the tests in red-green order during implementation, then together:

```bash
.venv/bin/python -m pytest -c apps/api/pyproject.toml \
  apps/api/tests/contract/test_auth_openapi.py \
  apps/api/tests/contract/test_role_interview_openapi.py \
  apps/api/tests/unit/jds \
  apps/api/tests/unit/interviews \
  apps/api/tests/integration/test_role_interview_schema.py \
  apps/api/tests/integration/test_profile_api.py \
  apps/api/tests/integration/test_jd_api.py \
  apps/api/tests/integration/test_interview_api.py \
  apps/api/tests/integration/test_schedule_idempotency.py \
  apps/api/tests/integration/test_role_interview_authorization.py \
  apps/api/tests/integration/test_admin_pagination.py \
  apps/api/tests/integration/test_admin_user_mutations.py \
  apps/api/tests/integration/test_role_change_interview_consistency.py
```

Expected: all success, denial, invalid-input, transaction rollback, concurrency, and safe-error
assertions pass against PostgreSQL. The existing authentication contract and this feature contract
both declare the production `__Host-mi_session` cookie security scheme, and their executable
contract tests fail on any future cookie-name divergence.

## Scenario 1: Google login, role routing, profile, and logout

1. Use deterministic signed claims for Candidate, Manager, and Admin, including email, name, and a
   permitted Google-hosted picture URL.
2. Complete login for each role.
3. Verify `/auth/me` returns that user's email and nullable picture plus the existing role/session
   fields.
4. Verify each role reaches its own home and a direct cross-role route is denied.
5. Open the top-right profile disclosure, navigate to `/profile`, and verify picture or placeholder,
   name, and email.
6. Select Logout and verify the old session cannot access any protected endpoint.

Expected: no Google token or raw claim reaches the browser, log, or audit record; logout returns to
login and requires fresh authentication.

## Scenario 2: Candidate allocation isolation

1. Create two active Candidates in the same organization.
2. Schedule different interviews for each.
3. Request `GET /api/v1/candidate/interviews` with each Candidate session.
4. Attempt direct access using the other Candidate's browser/session and wrong-role sessions.

Expected: each Candidate receives only JD ID/title, scheduled time, status, and interview ID for
their own rows. No JD content, Manager identity, or other Candidate identity is disclosed.

## Scenario 3: Manager manual and uploaded JDs

1. Sign in as Manager A and Manager B.
2. Manager A creates a manual JD with title and content.
3. Manager A uploads valid small PDF, DOCX, and UTF-8 TXT fixtures.
4. Verify Manager A's page contains all four JDs and Manager B's page contains none of them.
5. Attempt empty, oversized, spoofed, encrypted, macro-enabled, malformed, archive-bomb, binary TXT,
   and content-free uploads.
6. Attempt each write without Origin, with the wrong Origin, and with missing/mismatched CSRF.

Expected: valid inputs persist normalized content once; invalid inputs produce 400, 413, or 415 as
contracted and leave no partial JD. Original bytes/name and raw parser errors are not stored or
logged. Every CSRF failure is denied.

## Scenario 4: Atomic and idempotent scheduling

1. As Manager A, select an active same-organization Candidate and a JD created by Manager A.
2. Submit an offset-bearing future `scheduledAt` with a new UUID `Idempotency-Key`.
3. Repeat the identical request concurrently from two independent clients.
4. Reuse the same key with a different Candidate, JD, or time.
5. Attempt a missing field, past time, inactive Candidate, cross-organization Candidate, and
   Manager B's JD.
6. From an approved frontend origin, send a credentialed browser preflight that requests
   `Content-Type`, `X-CSRF-Token`, and `Idempotency-Key`; repeat from an unapproved origin.
7. With two independent database sessions and deterministic barriers, race scheduling against
   Candidate disable/role change, Manager disable/role change, and a fixture-driven JD owner/tenant
   change. Run each race once with the resource mutation locking first and once with scheduling
   locking first.

Expected: the first intent creates exactly one interview and one success audit; the identical
replay returns that row with `Idempotency-Replayed: true`; changed input returns 409; every invalid
selection leaves zero partial rows. The row appears in Manager A's list and only the selected
Candidate's list. The approved preflight admits all required headers and the unapproved origin is
denied.
When a resource mutation locks first, scheduling waits and then rejects with no interview or audit.
When scheduling locks first, exactly one complete interview and success audit may commit before the
resource mutation proceeds. No outcome contains a partial interview, orphan audit, or stale-owner
success.

## Scenario 5: Admin pagination, user details, and role change

1. Seed at least 1,000 users and 1,000 JDs with deterministic creation times and IDs.
2. Navigate every Admin user page and every Admin JD page at default size 25.
3. Verify totals, total pages, stable ordering, and exact set equality with no duplicate/missing row
   in the unchanged dataset.
4. Fetch one page, create a new ordered user/JD between page requests, and fetch the next page;
   verify both responses are independently authorized, contain no more than the requested page
   size, expose only the minimum projection, and contain no record outside the Admin's permission.
   Do not assert unchanged-set exact traversal across this deliberate mutation.
5. Select a user row and verify the accessible modal contains name, email, role, and status.
6. Change a provenance-linked Candidate to Manager, then Manager to Admin, then back to Candidate.
7. Verify provenance and CandidateProfile remain, each actual transition revokes old sessions, and
   a fresh login routes to the new role.
8. Repeat Admin endpoints as Candidate and Manager.

Expected: Admin sees application-wide minimum projections; non-Admins receive no Admin data;
details/modal state updates after role change; historical profile/provenance/interviews remain
valid. The existing authentication contract and the feature contract both permit every supported
target role and contain no obsolete CandidateProfile-conflict rule.

## Scenario 6: Tenant reassignment safety

1. Give a provenance-linked Candidate or Manager a scheduled-interview relationship.
2. Attempt Admin domain-mapping reassignment.
3. Repeat for a provenance-linked User with only single-owner JDs and no scheduled interview.
4. Inject a participant failure and inspect mapping, Users, JDs, sessions, generations, and audits.

Expected: a multi-owner scheduled record blocks the entire reassignment with no mixed tenant state.
A single-owner JD cascades with its creator when safe. Any participant failure rolls back every
mapping, auth, feature, session, and audit mutation.

## Scenario 7: Frontend component and browser journeys

```bash
npm --prefix apps/web run lint
npm --prefix apps/web run typecheck
npm --prefix apps/web run test:coverage
npm --prefix apps/web run test:e2e
```

Expected:

- Candidate, Manager, Admin, profile, empty/loading/error, pagination, form, dialog, and session
  recovery states pass with exact 100% frontend coverage.
- Keyboard-only users can use the skip link, profile disclosure, role navigation, forms, pagers,
  dialog, role selector, and logout.
- Focus enters each page heading, returns from disclosure/dialog, and reaches actionable errors.
- Live regions announce loading, validation, failure, success, and refresh without color-only state.
- Axe reports no WCAG violations with menus, modal, form errors, empty/populated tables, and each
  role screen visible.

Complete the manual NVDA or VoiceOver checklist in
`specs/002-role-interview-management/accessibility-validation.md`; automation alone is not release
evidence for SC-011.

## Scenario 8: Migration recovery

Against an isolated populated revision `004` database:

```bash
.venv/bin/python -m alembic -c apps/api/alembic.ini upgrade 005
.venv/bin/python -m alembic -c apps/api/alembic.ini downgrade 004
.venv/bin/python -m alembic -c apps/api/alembic.ini upgrade 005
```

Expected: upgrade preserves all prior data; isolated downgrade warns before dropping feature data
and fails safely if a provenance-linked non-Candidate cannot satisfy the restored old check;
re-upgrade succeeds after the isolated fixture is reset. Production incidents use a new forward
corrective revision and verified backup, not this destructive downgrade.

## Scenario 9: Performance and privacy evidence

```bash
.venv/bin/python apps/api/scripts/role_interview_baseline.py
```

Then run the guarded rendered-page harness against a dedicated local database whose exact name is
`mockinterview_role_interview_performance`:

```bash
PERFORMANCE_DATABASE_URL=postgresql+psycopg://mockinterview:local-development-only@localhost:5432/mockinterview_role_interview_performance \
  bash scripts/run-role-interview-performance.sh
```

The runner refuses any other database name, derives a sibling maintenance connection on the same
server, recreates only that exact dedicated database, and drops it during cleanup. It migrates and
deterministically seeds the dedicated database, writes short-lived role session states into a
permission-restricted temporary directory,
builds the frontend, starts the real API and the optimized bundle through a preview server with an
explicit API proxy, waits for both health endpoints, runs
`playwright.performance.config.ts`, and removes processes/state/database changes through a cleanup
trap. Before starting the lifecycle, it idempotently runs
`npx --prefix apps/web playwright install --with-deps chromium`, so no pre-existing browser binary
or Linux browser libraries are assumed. This command may require package-install privileges on a
clean Linux host.
The runner also exports every required API setting rather than reading `.env.local`: `APP_ENV=test`,
the validated database URL, generated test-only Google client values, the HTTPS Google issuer, a
callback on the dedicated API port, a runtime-generated Fernet key, the fixed OAuth/session
durations and return paths, a non-Secure performance-only cookie name, matching preview-origin
frontend/CSRF/application allowlists, and `ENABLE_FAKE_OIDC=true`. Secrets and browser session
states remain only in the permission-restricted temporary directory/environment and are deleted by
the cleanup trap. No manually running API, frontend, seed process, user env file, or real Google
credential is assumed.
The performance config discovers only `apps/web/performance`; the normal quality-gate config
discovers only `apps/web/e2e`, so the real-API performance spec cannot run accidentally in the
mock-based suite.
After the runner validates the exact dedicated database name, it exports both `DATABASE_URL` and
`MOCKINTERVIEW_MIGRATION_DATABASE_URL` to that same URL. Alembic `env.py` reads the explicit
migration override before its `alembic.ini` fallback, and migration tests prove this precedence, so
the API, migration, and seed processes cannot silently target different databases.

The browser performance fixture establishes authenticated sessions without timing Google itself,
uses at least 100 fresh/reload navigations distributed across Candidate, Manager, and Admin, and
runs 10 browser contexts concurrently to represent normal business load. For each navigation it
records the elapsed monotonic time from navigation start until both `Open profile menu` and the
role's requested home content are visible.

Expected: the checked-in baseline records correctness plus backend and browser p50/p95/max at the
seeded 1,000-user/1,000-JD scale; at least 95 of 100 rendered page views present both required UI
regions within 2 seconds (SC-004). Failed/timeout samples count against the threshold. Telemetry
contains only bounded operation/role/outcome/reason labels and correlation IDs, never email, name,
title, content, filename, picture URL, raw idempotency key, or document bytes.

## Scenario 10: Participant completion and workflow timing

Use the scripted protocol in
`specs/002-role-interview-management/usability-validation.md` with at least 20 representative
internal participants and at least five participants from each role. Use seeded but realistic data
and the same role permissions as production. Before each run, explain the task goal without
explaining the controls or navigation.

Record only anonymized participant code, assigned role, task, first-attempt result, whether help was
requested/given, and elapsed time. Define timing boundaries consistently:

- Login/profile/logout starts when the login page is visible and ends when logout returns to login
  after the participant has reached the role home and profile page.
- Manual JD creation starts when the Manager home is ready and ends when the manually created JD is
  visibly confirmed in the owned list.
- Valid JD upload starts when the Manager home is ready and ends when the uploaded JD is visibly
  confirmed in the owned list.
- Scheduling starts when Candidate/JD/date/time choices are visible and ends when the new interview
  is visibly confirmed in the Manager list.
- Admin inspection/change starts when the Admin tables are ready and ends when the selected user's
  updated role is visibly confirmed after opening details.
- A primary home task means Candidate identifies one allocated interview, Manager creates or
  uploads a JD and schedules one interview, or Admin locates and inspects one user and one JD.

Release thresholds:

- At least 19 of 20 participants complete login, correct home routing, profile viewing, and logout
  on the first attempt without assistance (SC-003).
- At least 18 of 20 complete their role's primary home task without assistance (SC-010).
- Every one of at least five measured manual-JD creation runs completes in under 3 minutes
  (SC-005).
- Every one of at least five measured valid-JD upload runs completes in under 3 minutes (SC-005).
- Every one of at least five measured Manager scheduling runs completes in under 2 minutes
  (SC-006).
- Every one of at least five measured Admin locate/detail/role-change runs over the seeded
  1,000-user result set completes in under 2 minutes (SC-008).

Expected: aggregate counts, rates, timing minima/medians/maxima, failed-task observations, and the
date/environment are recorded without names, emails, or confidential JD content. Any missed
threshold blocks feature acceptance and is resolved before repeating a fresh run.

## Full blocking gate

Run from the repository root with the isolated PostgreSQL `DATABASE_URL`:

```bash
MOCKINTERVIEW_PYTHON=.venv/bin/python bash scripts/quality-gate.sh
```

Expected: dependency licenses, Ruff, strict mypy, PostgreSQL tests, backend coverage, ESLint, strict
TypeScript, frontend coverage, and Playwright all pass. `.coverage-thresholds.json` remains the
single source of truth and requires 100% lines, branches, functions, and statements.
