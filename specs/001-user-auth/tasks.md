# Tasks: User Authentication and Role Access

**Input**: Design documents from `/specs/001-user-auth/`

**Prerequisites**: `plan.md`, `spec.md`, `.specify/memory/constitution.md`

**Tests**: Mandatory under the project constitution and `AGENTS.md`. For every story, write the listed tests first, run them, and confirm they fail for the intended reason before implementation.

**Organization**: Tasks are grouped by user story so each story can be implemented and verified as an independent increment. Python 3.12/FastAPI is authoritative where the plan contains conflicting backend wording.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it changes different files and has no dependency on an incomplete task in the same phase
- **[Story]**: Maps the task to a user story in `spec.md`
- Every task includes an exact file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Reconcile the approved scope and initialize the monorepo structure required by the plan.

- [X] T001 Reconcile pre-provisioned Google-only v1 scope, 8-hour maximum session lifetime, 2-hour idle timeout, and Python FastAPI backend wording in `specs/001-user-auth/spec.md` and `specs/001-user-auth/plan.md`
- [ ] T002 Create the Python 3.12 FastAPI package and test directory structure in `apps/api/app/__init__.py` and `apps/api/tests/__init__.py`
- [ ] T003 [P] Configure typed backend dependencies, pytest, Ruff, and coverage in `apps/api/pyproject.toml`
- [ ] T004 [P] Create the strict React TypeScript application and Vitest configuration in `apps/web/package.json`, `apps/web/tsconfig.json`, and `apps/web/vite.config.ts`
- [ ] T005 [P] Document non-secret OAuth, database, session, and frontend configuration variables in `.env.example`
- [ ] T006 [P] Add local PostgreSQL and application service definitions in `compose.yaml`
- [ ] T007 [P] Create shared authentication test fixtures and deterministic Google OIDC fakes in `apps/api/tests/conftest.py` and `apps/web/src/test/setup.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish validated configuration, persistence, API contracts, migrations, and shared observability before user-story work.

**Critical**: No user story implementation begins until this phase is complete.

- [ ] T008 Document dependency choices, session persistence rationale, cookie policy, and threat assumptions in `specs/001-user-auth/research.md`
- [ ] T009 [P] Define Organization, User, AuthenticationSession, and AuditEvent entities, constraints, and relationships in `specs/001-user-auth/data-model.md`
- [ ] T010 [P] Define login, callback, current-user, logout, authentication error, and authorization error contracts in `specs/001-user-auth/contracts/auth.openapi.yaml`
- [ ] T011 [P] Add failing configuration validation tests for missing or unsafe OAuth, database, session, cookie, and frontend-origin settings in `apps/api/tests/unit/test_config.py`
- [ ] T012 Implement typed environment validation with production-safe cookie defaults in `apps/api/app/core/config.py`
- [ ] T013 [P] Add failing model and migration tests for organization-scoped email uniqueness, roles, statuses, sessions, and audit events in `apps/api/tests/integration/test_auth_schema.py`
- [ ] T014 Implement SQLAlchemy models and enums for Organization, User, UserRole, UserStatus, AuthenticationSession, and AuditEvent in `apps/api/app/auth/models.py`
- [ ] T015 Create the forward authentication schema migration and documented downgrade handling in `apps/api/migrations/versions/001_create_auth_schema.py`
- [ ] T016 [P] Implement correlation-ID middleware and secret-safe structured logging in `apps/api/app/core/observability.py`
- [ ] T017 Create developer-controlled organization and role seed fixtures without production identities in `apps/api/scripts/seed_auth.py`

**Checkpoint**: Configuration rejects unsafe input, the tenancy-ready schema migrates cleanly, contracts are explicit, and logs can correlate requests without secrets.

---

## Phase 3: User Story 1 - Sign In with Google (Priority: P1) — MVP

**Goal**: A provisioned, active Candidate, Manager, or Admin can authenticate with Google, receive an application-owned session, load minimal current-user context, and reach the correct role entry view; all failed or unprovisioned logins remain unauthenticated.

**Independent Test**: Use the deterministic OIDC fake for one active provisioned identity per role plus cancelled, malformed, unknown, and disabled identities; verify session creation, safe failures, `/auth/me`, and role landing behavior without contacting Google.

### Tests for User Story 1 — write and run first

- [ ] T018 [P] [US1] Add failing unit tests for OIDC state, nonce, issuer, audience, signature, expiry, and required-claim validation in `apps/api/tests/unit/auth/test_google_oidc.py`
- [ ] T019 [P] [US1] Add failing unit tests for normalized user lookup and rejection of unknown or disabled users in `apps/api/tests/unit/auth/test_auth_service.py`
- [ ] T020 [P] [US1] Add failing API contract tests for login, callback, safe errors, session cookie creation, and `/auth/me` response minimization in `apps/api/tests/contract/test_auth_api.py`
- [ ] T021 [P] [US1] Add failing integration tests for successful Candidate, Manager, and Admin login plus cancelled, malformed, unknown, and disabled login outcomes in `apps/api/tests/integration/test_google_login.py`
- [ ] T022 [P] [US1] Add failing frontend tests for the accessible Google sign-in page, auth bootstrap, safe error recovery, and role-specific redirects in `apps/web/src/auth/AuthFlow.test.tsx`
- [ ] T023 [P] [US1] Add a failing browser journey for the three provisioned role logins and an unprovisioned identity denial in `apps/web/e2e/google-login.spec.ts`

### Implementation for User Story 1

- [ ] T024 [P] [US1] Implement a narrow Google OIDC adapter with validated claims and no browser token exposure in `apps/api/app/auth/google_oidc.py`
- [ ] T025 [US1] Implement provisioned-user resolution, active-status enforcement, and application session creation in `apps/api/app/auth/service.py`
- [ ] T026 [US1] Implement login, callback, and current-user endpoints with safe 401/403 responses in `apps/api/app/auth/router.py`
- [ ] T027 [US1] Register authentication routes and request middleware in `apps/api/app/main.py`
- [ ] T028 [P] [US1] Emit secret-safe login-success and login-denial audit records with correlation identifiers in `apps/api/app/auth/audit.py`
- [ ] T029 [P] [US1] Define strict frontend user, role, and authentication error contracts in `apps/web/src/auth/types.ts`
- [ ] T030 [US1] Implement credentialed auth API calls and current-user loading in `apps/web/src/auth/api.ts`
- [ ] T031 [US1] Implement authenticated, unauthenticated, loading, and safe-error state management in `apps/web/src/auth/AuthProvider.tsx`
- [ ] T032 [US1] Implement the keyboard-accessible Google sign-in and access-not-provisioned views in `apps/web/src/auth/LoginPage.tsx` and `apps/web/src/auth/AccessNotProvisionedPage.tsx`
- [ ] T033 [US1] Implement Candidate, Manager, and Admin post-login routing in `apps/web/src/auth/RoleLanding.tsx`

**Checkpoint**: User Story 1 passes independently and provides the deployable authentication MVP.

---

## Phase 4: User Story 2 - Enforce Role Permissions (Priority: P1)

**Goal**: Every protected backend operation enforces authentication, organization, role, and resource ownership with deny-by-default behavior, while the frontend exposes only the relevant role navigation.

**Independent Test**: Exercise the permission matrix as all three roles across same-user, other-user, same-organization, and cross-organization resources; verify every allowed combination succeeds and every denied combination returns 403 without protected content.

### Tests for User Story 2 — write and run first

- [ ] T034 [P] [US2] Add failing unit tests for authenticated-user, role, organization, and candidate-ownership policy decisions in `apps/api/tests/unit/auth/test_authorization.py`
- [ ] T035 [P] [US2] Add failing API tests for all allowed and denied permission-matrix combinations in `apps/api/tests/integration/test_role_authorization.py`
- [ ] T036 [P] [US2] Add failing integration tests for direct-link, other-candidate, and cross-organization data access attempts in `apps/api/tests/integration/test_resource_isolation.py`
- [ ] T037 [P] [US2] Add failing frontend tests for protected routes and Candidate, Manager, and Admin navigation visibility in `apps/web/src/auth/ProtectedRoutes.test.tsx`
- [ ] T038 [P] [US2] Add a failing browser journey proving a Candidate cannot enter Manager or Admin routes by navigation or direct URL in `apps/web/e2e/role-access.spec.ts`

### Implementation for User Story 2

- [ ] T039 [P] [US2] Implement deny-by-default role capabilities matching the specification permission matrix in `apps/api/app/auth/policies.py`
- [ ] T040 [US2] Implement reusable FastAPI authenticated-user and role dependencies in `apps/api/app/auth/dependencies.py`
- [ ] T041 [US2] Implement organization-context and candidate-resource ownership enforcement in `apps/api/app/auth/authorization.py`
- [ ] T042 [US2] Apply the reusable guards to representative protected profile and allocation API boundaries in `apps/api/app/protected/router.py`
- [ ] T043 [P] [US2] Emit secret-safe authorization-denial audit records with actor, organization, resource, and correlation context in `apps/api/app/auth/audit.py`
- [ ] T044 [US2] Implement strict protected-route guards and safe unauthenticated/forbidden states in `apps/web/src/auth/ProtectedRoute.tsx`
- [ ] T045 [US2] Implement role-aware Candidate, Manager, and Admin navigation without treating UI visibility as authorization in `apps/web/src/navigation/RoleNavigation.tsx`

**Checkpoint**: User Story 2 passes independently against the full permission and isolation matrix.

---

## Phase 5: User Story 3 - End and Govern Sessions (Priority: P2)

**Goal**: Users can log out, expired or idle sessions are denied, disabled users cannot continue, and session failures provide safe recovery guidance.

**Independent Test**: For every role, verify explicit logout, repeated logout, 8-hour maximum expiry, 2-hour idle expiry, disabled-user invalidation, cookie clearing, and subsequent protected-request denial using a controllable clock.

### Tests for User Story 3 — write and run first

- [ ] T046 [P] [US3] Add failing unit tests with a controllable clock for session creation, idle refresh, maximum expiry, invalidation, and secret hashing in `apps/api/tests/unit/auth/test_sessions.py`
- [ ] T047 [P] [US3] Add failing API tests for logout idempotency, cookie clearing, expired sessions, disabled users, and safe recovery errors in `apps/api/tests/integration/test_session_lifecycle.py`
- [ ] T048 [P] [US3] Add failing frontend tests for logout, session-expiry recovery, and protected-state clearing in `apps/web/src/auth/SessionLifecycle.test.tsx`
- [ ] T049 [P] [US3] Add a failing browser journey proving logout and expiry prevent browser-history and direct-request access in `apps/web/e2e/session-lifecycle.spec.ts`

### Implementation for User Story 3

- [ ] T050 [US3] Implement hashed server-side session persistence, idle refresh, maximum expiry, and invalidation in `apps/api/app/auth/sessions.py`
- [ ] T051 [US3] Enforce session validity and active-user status on every authenticated request in `apps/api/app/auth/dependencies.py`
- [ ] T052 [US3] Implement idempotent logout with server invalidation and cookie clearing in `apps/api/app/auth/router.py`
- [ ] T053 [P] [US3] Emit secret-safe logout, expiry, revocation, and disabled-user session audit events in `apps/api/app/auth/audit.py`
- [ ] T054 [US3] Implement frontend logout and clear all cached protected identity state in `apps/web/src/auth/AuthProvider.tsx`
- [ ] T055 [US3] Implement accessible expired-session and reauthentication guidance in `apps/web/src/auth/SessionExpiredPage.tsx`

**Checkpoint**: User Story 3 passes independently for all roles and no ended session can access protected information.

---

## Phase 6: User Story 4 - Manual Password Is Not Offered (Priority: P3)

**Goal**: Enforce the approved v1 decision that manual login and password-management journeys are absent while Google login remains the only entry point.

**Independent Test**: Verify no password fields, reset links, password routes, credential models, or password endpoints exist in the rendered application or OpenAPI contract.

### Tests for User Story 4 — write and run first

- [ ] T056 [P] [US4] Add a failing contract assertion that the OpenAPI schema exposes no password login, creation, change, recovery, reset, expiry, or lockout endpoints in `apps/api/tests/contract/test_google_only_auth.py`
- [ ] T057 [P] [US4] Add a failing frontend assertion that authentication views expose no password controls or recovery links in `apps/web/src/auth/GoogleOnlyAuth.test.tsx`

### Implementation for User Story 4

- [ ] T058 [US4] Document Google-only authentication as an intentional v1 non-goal and trace FR-011/SC-006 to the absence tests in `specs/001-user-auth/contracts/auth.openapi.yaml` and `specs/001-user-auth/spec.md`

**Checkpoint**: User Story 4 independently proves that no unsupported credential surface is exposed.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Complete traceability, accessibility, security/privacy review, operational documentation, and blocking quality gates.

- [ ] T059 [P] Map every functional requirement, acceptance scenario, success criterion, and explicit non-goal to code and automated evidence in `specs/001-user-auth/traceability.md`
- [ ] T060 [P] Document OAuth setup, migration, seeding, local test, session operations, and incident-revocation procedures in `docs/authentication.md`
- [ ] T061 [P] Add automated accessibility coverage for login, errors, protected routes, and session expiry in `apps/web/e2e/auth-accessibility.spec.ts`
- [ ] T062 Complete and record the named authentication security and privacy review, including OAuth CSRF, cookie, fixation, replay, redirect, enumeration, logging, and tenancy controls in `specs/001-user-auth/security-privacy-review.md`
- [ ] T063 Run backend unit, contract, integration, migration, type, lint, and coverage gates and record results in `specs/001-user-auth/validation.md`
- [ ] T064 Run `npx vitest run`, `npx vitest run --coverage`, frontend lint/type checks, browser journeys, and the WCAG 2.2 AA manual keyboard/screen-reader checklist and record results in `specs/001-user-auth/validation.md`
- [ ] T065 Run Spec Kit consistency analysis/convergence, resolve all authentication gaps, and record the clean result in `specs/001-user-auth/validation.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Starts immediately. T001 is a scope gate; T002 must precede tasks that create backend files.
- **Foundational (Phase 2)**: Depends on Setup and blocks every user story. T011 must fail before T012; T013 must fail before T014-T015.
- **User Story 1 (Phase 3)**: Depends on Foundational and supplies the MVP authentication/session bootstrap used by later stories.
- **User Story 2 (Phase 4)**: Depends on Foundational and the authenticated identity/session context from US1; it remains independently testable through fixtures.
- **User Story 3 (Phase 5)**: Depends on the basic application session created by US1; its lifecycle rules can otherwise be developed independently of US2.
- **User Story 4 (Phase 6)**: Depends only on the reconciled Google-only scope and contracts; it may run after Foundational in parallel with US1-US3.
- **Polish (Phase 7)**: T059-T061 can begin after relevant story contracts stabilize; T062-T065 require all selected stories complete.

### User Story Completion Order

```text
Setup -> Foundational -> US1 (MVP) -> US2
                            |          |
                            +-> US3 ---+-> Polish
Foundational -----------------> US4 ---+
```

### Within Each User Story

- Write all listed tests first and run them to confirm the intended failure.
- Implement domain and adapter behavior before endpoints or UI integration.
- Keep OAuth-provider behavior deterministic in routine tests; use a separately marked staging contract check for real Google configuration.
- Complete the independent-test checkpoint before advancing the story.

## Parallel Opportunities

- In Setup, T003-T007 can run in parallel after T002 where their target directory is required.
- In Foundational, T009-T011 and T013 can be authored in parallel; T016 is independent of schema work.
- In US1, T018-T023 can be authored in parallel before implementation; T024, T028, and T029 target separate files.
- In US2, T034-T038 can be authored in parallel; T039 and T043 target separate files.
- In US3, T046-T049 can be authored in parallel; T053 targets a separate audit module.
- US4 can run alongside US1-US3 once Foundational and T001 are complete.
- T059-T061 can run in parallel once story behavior and contracts are stable.

## Parallel Execution Examples

### User Story 1

```text
Task T018: Validate OIDC claims in apps/api/tests/unit/auth/test_google_oidc.py
Task T019: Validate user resolution in apps/api/tests/unit/auth/test_auth_service.py
Task T020: Validate HTTP contracts in apps/api/tests/contract/test_auth_api.py
Task T021: Validate login integration in apps/api/tests/integration/test_google_login.py
Task T022: Validate React auth flow in apps/web/src/auth/AuthFlow.test.tsx
Task T023: Validate browser login journey in apps/web/e2e/google-login.spec.ts
```

### User Story 2

```text
Task T034: Test policy decisions in apps/api/tests/unit/auth/test_authorization.py
Task T035: Test permission matrix in apps/api/tests/integration/test_role_authorization.py
Task T036: Test isolation in apps/api/tests/integration/test_resource_isolation.py
Task T037: Test protected UI routes in apps/web/src/auth/ProtectedRoutes.test.tsx
Task T038: Test direct URL denial in apps/web/e2e/role-access.spec.ts
```

### User Story 3

```text
Task T046: Test session rules in apps/api/tests/unit/auth/test_sessions.py
Task T047: Test session APIs in apps/api/tests/integration/test_session_lifecycle.py
Task T048: Test frontend lifecycle in apps/web/src/auth/SessionLifecycle.test.tsx
Task T049: Test browser lifecycle in apps/web/e2e/session-lifecycle.spec.ts
```

### User Story 4

```text
Task T056: Assert absent password API contracts in apps/api/tests/contract/test_google_only_auth.py
Task T057: Assert absent password UI in apps/web/src/auth/GoogleOnlyAuth.test.tsx
```

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational phases.
2. Complete User Story 1 using strict red-green-refactor TDD.
3. Run the US1 independent test across Candidate, Manager, Admin, and denied identities.
4. Demonstrate the Google authentication MVP before adding permission and lifecycle increments.

### Incremental Delivery

1. **US1**: Google login, provisioned-user enforcement, app session, `/auth/me`, and role landing.
2. **US2**: Server-side role, organization, and ownership enforcement plus role-aware navigation.
3. **US3**: Logout, expiry, idle timeout, revocation, and safe recovery.
4. **US4**: Executable proof that manual-password surfaces are absent.
5. **Polish**: Traceability, security/privacy approval, accessibility, 100% coverage gates, and Spec Kit convergence.

## Notes

- `[P]` means separate files and no incomplete-task dependency; coordinate before parallel edits to shared files such as `apps/api/app/auth/audit.py`.
- Tests are mandatory and must fail for the intended reason before their implementation tasks start.
- `.coverage-thresholds.json` is the source of truth: lines, branches, functions, and statements must all remain at 100%, with `npx vitest run --coverage` blocking task completion.
- Backend tests must also pass through the configured pytest coverage gate established in T003.
- Do not add public registration, username/password authentication, MFA, additional identity providers, or unrelated application-domain behavior.
- Never place OAuth tokens, session secrets, real identities, or credentials in source, fixtures, logs, client bundles, or version control.
