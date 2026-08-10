# Implementation Plan: Role-Based Interview Management

**Branch**: `001-user-auth` (current working branch) | **Date**: 2026-08-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-role-interview-management/spec.md`

## Summary

Extend the existing Google-only authenticated application with a shared authenticated shell and
profile experience, persistent Manager-owned Job Descriptions, atomic Candidate interview
scheduling, Candidate-owned allocation views, and Admin user/JD tables. Reuse the current
request-scoped PostgreSQL transactions, deny-by-default authorization, CSRF, audit, error,
observability, and runtime-decoder patterns. Add one forward schema revision, role-specific API
modules, secure bounded JD text extraction, declarative frontend routing, and layered tests that
retain the repository's exact 100% coverage gate.

## Technical Context

**Language/Version**: Python 3.12 for the API and migrations; TypeScript 5.9 with React 19 for the web application

**Primary Dependencies**: Existing FastAPI 0.116.1, SQLAlchemy 2.0.43 async, Alembic 1.16.5,
Pydantic, React Router 7.18.2, and the existing auth/security stack; add pinned
`python-multipart==0.0.32`, `pypdf==6.14.2`, and `python-docx==1.2.0` after the required license and
security review

**Storage**: PostgreSQL 17 for users, canonical extracted JD content, scheduling records,
idempotency evidence, sessions, and audits; uploaded originals are validated in bounded memory and
discarded after extraction

**Testing**: Pytest/pytest-asyncio with real PostgreSQL integration tests and coverage; Vitest,
React Testing Library, Playwright, and axe-core; Ruff, strict mypy, ESLint, and strict TypeScript

**Target Platform**: Linux-hosted web API and evergreen desktop/mobile web browsers used by
internal Ideas2IT users

**Project Type**: Web application with one FastAPI backend and one React frontend

**Performance Goals**: 95% of authenticated page views show requested content within 2 seconds;
Admin pagination remains correct at 1,000 users and 1,000 JDs; Manager JD creation completes within
3 minutes and scheduling within 2 minutes at the user-journey level

**Constraints**: Google OAuth and server sessions remain the only authentication path; all writes
use Origin plus double-submit CSRF protection; uploads are PDF/DOCX/UTF-8 TXT, at most 5 MiB, and
yield at most 500,000 normalized characters; page size defaults to 25 and is capped at 100; all
scheduled timestamps carry an explicit UTC offset; WCAG 2.2 AA; 100% lines, branches, functions,
and statements for backend and frontend

**Scale/Scope**: Three roles, six primary user journeys, approximately twelve feature endpoints,
1,000-user and 1,000-JD acceptance datasets, and v1 single-tenant operation with tenancy-safe
ownership fields; no JD editing/deletion, rescheduling/cancellation, notifications, interview
execution, scoring, or reporting

## Constitution Check

*GATE: Passed before Phase 0 research and re-checked after Phase 1 design.*

- **I. Modular architecture and reuse — PASS**: authentication remains in `app/auth`; new JD and
  interview modules have separate schemas, services, and routers while sharing the established
  database, error, policy, and audit boundaries. No speculative service or distribution layer is
  introduced.
- **II. Strict types and validated boundaries — PASS**: Pydantic request/response schemas,
  runtime frontend decoders, verified Google claims, bounded upload adapters, explicit timestamp
  parsing, and database constraints validate every untrusted boundary. Python and TypeScript stay
  strict.
- **III. Security, privacy, least privilege — PASS**: self/owner/role/organization predicates are
  applied before data retrieval; mutations retain CSRF; lists use minimum projections; uploaded
  originals, filenames, JD text, emails, image URLs, and idempotency keys never enter logs/audits.
  A named upload/profile/scheduling security review is required before release.
- **IV. Versioned data and API contracts — PASS**: forward revision `005` follows immutable
  revision `004`; downgrade is isolated/pre-release only and production recovery is forward. The
  feature OpenAPI contract includes schemas, pagination, multipart, idempotency, auth, CSRF, and
  safe errors.
- **V. Layered testing — PASS**: unit, contract, real-PostgreSQL integration/concurrency,
  component, browser, accessibility, migration, and performance checks are defined. Deterministic
  uploaded-document fixtures replace external services in routine tests.
- **VI. Acceptance-criteria delivery — PASS**: all implementation surfaces trace to FR-001–FR-034
  and SC-001–SC-011; denial, invalid-input, retry, concurrency, accessibility, and migration cases
  are explicit.
- **VII. Simplicity and dependencies — PASS**: existing React Router is activated rather than
  replaced. Three narrowly justified upload dependencies are required because the standard
  library cannot safely parse multipart PDF/DOCX content; original documents and object-storage
  infrastructure are not retained or introduced.
- **VIII. Observable failures — PASS**: new routes extend correlated structured events, bounded
  counters and latency measurements, safe error envelopes, and append-only audits without content
  or identity-bearing labels.
- **IX. Accessible UX — PASS**: native landmarks, disclosure controls, links/buttons, tables,
  forms, `<dialog>`, focus restoration, live regions, keyboard journeys, axe coverage, and manual
  screen-reader evidence are planned.

**Post-design re-check**: PASS. The data model, interface contract, and quickstart preserve all
nine gates. No constitutional exception or complexity waiver is required.

## Project Structure

### Documentation (this feature)

```text
specs/002-role-interview-management/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── security-privacy-review.md       # implementation/release evidence
├── accessibility-validation.md      # implementation/release evidence
├── usability-validation.md          # participant task/rate/timing evidence
├── validation.md                    # implementation/release evidence
├── contracts/
│   └── role-interview.openapi.yaml
└── tasks.md                         # created by $speckit-tasks, not this command

specs/001-user-auth/contracts/
└── auth.openapi.yaml                # existing /auth/me and role-transition contracts updated
```

### Source Code (repository root)

```text
apps/api/
├── app/
│   ├── auth/
│   │   ├── models.py               # profile picture and role/provenance compatibility
│   │   ├── google_oidc.py          # verified picture claim
│   │   ├── service.py              # refresh verified profile identity
│   │   ├── router.py               # extended /auth/me
│   │   ├── dependencies.py         # Candidate/Manager/Admin capability guards
│   │   ├── policies.py             # new role/ownership capabilities
│   │   ├── errors.py               # stable feature failure contracts
│   │   └── audit.py                # safe metadata allowlist
│   ├── admin/
│   │   ├── router.py               # paginated users/JDs and user details
│   │   └── service.py              # pagination and all supported role transitions
│   ├── jds/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── documents.py            # bounded PDF/DOCX/TXT extraction adapter
│   │   ├── service.py
│   │   └── router.py
│   ├── interviews/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   ├── manager_router.py
│   │   ├── candidate_router.py
│   │   └── tenancy.py              # fail-closed scheduled-record migration participant
│   ├── core/
│   │   └── observability.py
│   └── main.py                     # router, participant, and CORS allow-header composition
├── migrations/
│   ├── env.py                    # guarded explicit migration URL override
│   └── versions/005_add_jds_and_scheduled_interviews.py
├── scripts/role_interview_baseline.py
├── scripts/seed_role_interview_performance.py # isolated 1,000-record data/session fixture
└── tests/
    ├── conftest.py                    # new factories, Google picture claim, safe TRUNCATE order
    ├── integration/test_auth_schema.py # existing exact table/constraint/index expectations
    ├── integration/test_admin_user_mutations.py # revised Candidate transition regression
    ├── contract/test_auth_openapi.py  # existing /auth/me executable contract regression
    ├── unit/{auth,jds,interviews,admin,core}/
    ├── contract/test_role_interview_openapi.py
    └── integration/

apps/web/
├── src/
│   ├── App.tsx
│   ├── auth/{api,types,decoders}.ts # extended /auth/me contract and feature fetch recovery
│   ├── auth/AuthFlow.test.tsx       # strict identity decoder/transport regression
│   ├── App.test.tsx                 # extended current-user fixtures and routed shell
│   ├── auth/RoleLanding.test.tsx    # updated/retired role-landing fixtures
│   ├── auth/ProtectedRoutes.test.tsx # email/picture-aware role fixtures
│   ├── auth/SessionLifecycle.test.tsx # email/picture-aware session fixtures
│   ├── layout/{AuthenticatedShell,ProfileMenu}.tsx
│   ├── components/{AsyncState,Pagination,ProfileImage,StatusBadge}.tsx
│   ├── profile/ProfilePage.tsx
│   ├── candidate/{CandidateHome,api,decoders,types}.ts(x)
│   ├── manager/{ManagerHome,JdList,JdForms,ScheduleInterviewForm,ScheduledInterviewList}.tsx
│   ├── manager/{api,decoders,types}.ts
│   ├── admin/{AdminHome,UsersTable,JdsTable,UserDetailsDialog}.tsx
│   ├── admin/{api,decoders,types}.ts
│   ├── navigation/RoleNavigation.tsx
│   └── styles.css
├── package.json                     # production-preview command
├── vite.config.ts                   # development and preview API proxies
├── src/viteConfig.test.ts           # both proxy contracts
├── playwright.performance.config.ts # external real API/preview lifecycle contract
└── e2e/
    ├── {google-login,auth-accessibility,session-lifecycle,role-access}.spec.ts # updated identity fixtures
    ├── role-interview-management.spec.ts
    ├── role-interview-accessibility.spec.ts
    └── support/accessibility.ts

apps/web/performance/
└── role-interview-performance.spec.ts # outside normal ./e2e discovery

scripts/
└── run-role-interview-performance.sh # guarded isolated DB/API/preview/Playwright orchestration
```

**Structure Decision**: Keep the existing `apps/api` plus `apps/web` layout. Domain logic is
separated into JD and interview modules, while authentication/profile and Admin extensions remain
in their established modules. Frontend domain folders own their transport, strict types, runtime
decoders, screens, and tests; the authenticated shell and small accessible primitives are shared.

## Phase 0: Research Outcomes

Research decisions and rejected alternatives are recorded in [research.md](research.md). All
technical unknowns are resolved and no planning questions remain open.

## Phase 1: Design Outcomes

- [data-model.md](data-model.md) defines User changes, JobDescription, ScheduledInterview,
  idempotency, validation, ownership, indexing, role transitions, and tenant-reassignment behavior.
- [contracts/role-interview.openapi.yaml](contracts/role-interview.openapi.yaml) defines the
  authenticated profile, Candidate, Manager, and Admin HTTP boundaries.
- [quickstart.md](quickstart.md) defines runnable migration, contract, role/ownership, upload,
  scheduling, pagination, accessibility, performance, and full-gate validation scenarios.

## Implementation Sequence and Verification Strategy

1. **Contract/schema red tests**: add migration metadata, OpenAPI, claim/profile, upload, policy,
   pagination, and scheduling tests that fail against revision `004` and current routes. Update the
   existing `test_auth_schema.py` exact table/constraint/index expectations and shared
   `tests/conftest.py` factories/TRUNCATE order rather than leaving parallel schema assumptions.
   Update the existing `specs/001-user-auth/contracts/auth.openapi.yaml` and
   `test_auth_openapi.py` for required `email` and nullable `profilePictureUrl`, and assert that its
   `/auth/me` schema and `__Host-mi_session` security scheme stay equivalent to the new feature
   contract. Replace its obsolete statement that Candidate→Manager/Admin is rejected with the
   provenance-preserving success behavior, and add executable assertions that every supported
   target role is allowed while actual changes revoke old sessions.
2. **Foundation**: pin reviewed dependencies; add revision `005`, models, factories, strict schemas,
   upload adapter, capabilities, errors, audit allowlists, and observability names. Add
   `Idempotency-Key` to the explicit CORS request-header allowlist and test a browser preflight with
   credentials. Make Alembic `env.py` prefer an explicit
   `MOCKINTERVIEW_MIGRATION_DATABASE_URL` over the `alembic.ini` fallback, and test that precedence;
   `DATABASE_URL` remains the API runtime URL and is not silently assumed to configure Alembic.
   Prove populated `004 -> 005`, downgrade/re-upgrade, role/provenance compatibility, and named
   constraints.
3. **Profile/auth shell**: extend verified claims and `/auth/me`; update the existing frontend auth
   types, runtime decoder, API transport, response fixtures, and `AuthFlow` tests for required email
   plus nullable profile picture; add BrowserRouter, AuthenticatedShell, profile disclosure/page,
   placeholder image, role routes, and session-aware feature fetch recovery. Preserve Google-only
   login/logout semantics. Update every existing current-user fixture in `App.test.tsx`,
   `RoleLanding.test.tsx`, `ProtectedRoutes.test.tsx`, `SessionLifecycle.test.tsx`, and existing
   Playwright `google-login`, `auth-accessibility`, `session-lifecycle`, and `role-access` specs so
   the stricter decoder never depends on stale mock payloads.
4. **JD slice**: implement Manager manual/upload creation and owned list, Admin JD list, bounded
   extraction, CSRF, projections, audit/metrics, empty/error/success states, and ownership denial.
5. **Scheduling slice**: implement minimal same-organization active-Candidate selection, Manager
   scheduling/list, Candidate self-scoped list, idempotency/replay/conflict, future timestamp checks,
   atomic audit, and the tenant-migration blocker for multi-owner scheduled records.
6. **Admin slice**: add application-wide paginated users/JDs, user detail dialog, and all supported
   role changes while retaining CandidateProfile/provenance and revoking existing sessions. Replace
   the existing `test_admin_user_mutations.py` Candidate-transition conflict expectation with
   successful Candidate→Manager/Admin transitions that prove preserved profile/provenance,
   generation increment, and full old-session revocation.
7. **Cross-cutting validation**: use two independent PostgreSQL sessions and deterministic barriers
   to race scheduling against Candidate disable/role change, Manager disable/role change, and a
   fixture-driven JD owner/tenant change. Exercise both lock orders: a resource mutation that locks
   first makes scheduling wait and then reject with no interview/audit, while scheduling that locks
   first creates exactly one complete interview/audit before the mutation proceeds; no outcome may
   contain a partial row, orphan audit, or stale-owner success. Also run 1,000-record
   pagination/performance,
   authorization matrix, safe telemetry, contract/generated-schema checks, credentialed CORS
   preflight for every custom mutation header, responsive keyboard and screen-reader flows, axe,
   and manual accessibility checklist. Run a scripted, unassisted usability study with at least 20
   representative participants (at least five per role): at least 19/20 must complete
   login/home/profile/logout on their first attempt, at least 18/20 must complete their role's
   primary home task. Require at least five manual-JD creation runs and at least five valid-upload
   JD creation runs, with every run in each group under 3 minutes; at least five scheduling runs
   under 2 minutes; and at least five Admin locate/detail/role-change runs under 2 minutes. Record
   task definitions, start/end rules, assistance, failures, durations, and anonymized aggregate
   results in `usability-validation.md`.
   Separately run at least 100 authenticated rendered-page measurements, distributed across all
   three roles, against a production build with the real API and seeded 1,000-user/1,000-JD dataset
   under the representative normal load of 10 concurrent browser contexts. Measure from navigation
   start until both the top-right profile control and requested role-home information are visible;
   at least 95 measurements must complete within 2 seconds. Record p50/p95/max, failures, build,
   dataset, and environment through `performance/role-interview-performance.spec.ts` and the checked-in
   performance baseline.
   Make this executable through `run-role-interview-performance.sh`: require and guard a target URL
   whose database name is exactly `mockinterview_role_interview_performance`; connect only to the
   sibling `postgres` maintenance database to recreate that exact target at start and drop it at
   exit. Only after validating that exact target, export both runtime `DATABASE_URL` and
   `MOCKINTERVIEW_MIGRATION_DATABASE_URL` to the same dedicated URL so the API and Alembic cannot
   diverge; idempotently install the pinned Playwright Chromium browser and its Linux dependencies.
   Export a complete fail-closed test configuration for API startup without `.env.local`:
   `APP_ENV=test`, generated test-only Google client values, the real HTTPS Google issuer, callback
   and matching frontend/CSRF/application origins on the dedicated ports, a runtime-generated
   Fernet key, fixed OAuth/session durations and return paths, a performance-only non-Secure cookie,
   and `ENABLE_FAKE_OIDC=true`. Keep generated secrets and session state only in the
   permission-restricted temporary environment/directory; migrate and seed 1,000 users/JDs plus
   role sessions into a permission-restricted temporary state directory; build the web bundle;
   start the real API on a dedicated port and Vite preview of `dist` with an explicit preview proxy;
   wait on health checks; run `playwright.performance.config.ts`; then trap-stop both servers,
   delete temporary session state, and drop only the validated dedicated database. The
   normal Playwright configuration and quality gate remain deterministic/mock-based; this separate
   release command owns every real-API prerequisite.
8. **Release gate**: update security/privacy, accessibility, usability, migration recovery,
   dependency license, traceability, and validation evidence; run `bash scripts/quality-gate.sh`
   against an isolated PostgreSQL database. Completion is blocked unless all configured 100%
   thresholds and the recorded SC-003/SC-005/SC-006/SC-008/SC-010 participant gates pass.

## Complexity Tracking

No constitution violations require justification. The three new parser dependencies are not a
waiver: each covers a required, security-sensitive external format that the existing dependency set
and standard library do not safely implement, and each remains behind one bounded adapter.
