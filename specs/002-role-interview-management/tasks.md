# Tasks: Role-Based Interview Management

**Input**: Design documents from `/specs/002-role-interview-management/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/role-interview.openapi.yaml`, `quickstart.md`

**Tests**: TDD is mandatory. Every test task below must be completed and observed failing for the intended reason before its paired implementation task begins. Exact 100% backend and frontend coverage from `.coverage-thresholds.json` is blocking.

**Organization**: Tasks are grouped by user story so each increment can be implemented and verified independently after the shared foundation is complete.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Safe to execute in parallel because the task owns different files and has no dependency on another incomplete task
- **[Story]**: Maps the task to one user story from `spec.md`
- Every task names the exact files it changes

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare pinned dependencies, module boundaries, and deterministic fixtures required by later red tests.

- [X] T001 Review licenses/security and pin `python-multipart==0.0.32`, `pypdf==6.14.2`, and `python-docx==1.2.0` in `apps/api/pyproject.toml`, `apps/api/requirements.lock`, and `scripts/check-dependency-licenses.sh`
- [X] T002 [P] Create the API package boundaries in `apps/api/app/jds/__init__.py` and `apps/api/app/interviews/__init__.py`
- [X] T003 [P] Add bounded valid/invalid PDF, DOCX, and TXT fixtures in `apps/api/tests/fixtures/jd_documents/` without confidential content
- [X] T004 [P] Add shared typed response factories for current users, paged JDs, Candidates, and interviews in `apps/web/src/test/factories.ts`
- [X] T005 Add the production preview command and explicit development/preview API proxy configuration in `apps/web/package.json` and `apps/web/vite.config.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the schema, shared authorization/contracts, test factories, CORS, and migration safety required by every story.

**⚠️ CRITICAL**: No user-story implementation begins until this phase is complete.

### Foundational tests — write and observe failures first

- [X] T006 [P] Write migration URL precedence tests and confirm they fail in `apps/api/tests/unit/core/test_migration_env.py`
- [X] T007 [P] Extend exact table, column, constraint, index, populated-upgrade, downgrade/re-upgrade, and provenance compatibility tests and confirm they fail in `apps/api/tests/integration/test_auth_schema.py` and `apps/api/tests/integration/test_role_interview_schema.py`
- [X] T008 [P] Write failing shared capability, safe-error, audit-allowlist, and bounded-observability tests in `apps/api/tests/unit/auth/test_policies.py`, `apps/api/tests/unit/auth/test_errors.py`, `apps/api/tests/unit/auth/test_audit.py`, and `apps/api/tests/unit/core/test_observability.py`
- [X] T009 [P] Write failing cross-contract tests for `/auth/me`, supported role transitions, and the `__Host-mi_session` scheme in `apps/api/tests/contract/test_auth_openapi.py` and `apps/api/tests/contract/test_role_interview_openapi.py`
- [X] T010 [P] Write failing credentialed CORS preflight coverage for `Content-Type`, `X-CSRF-Token`, and `Idempotency-Key` in `apps/api/tests/integration/test_cookie_csrf_security.py`

### Foundational implementation

- [X] T011 Make `MOCKINTERVIEW_MIGRATION_DATABASE_URL` override `alembic.ini` safely in `apps/api/migrations/env.py` and make T006 pass
- [X] T012 Define `User.profile_picture_url`, `JobDescription`, and `ScheduledInterview` with all named ownership constraints and indexes in `apps/api/app/auth/models.py`, `apps/api/app/jds/models.py`, and `apps/api/app/interviews/models.py`
- [X] T013 Implement forward revision `005` and guarded isolated downgrade in `apps/api/migrations/versions/005_add_jds_and_scheduled_interviews.py`, including removal/restoration of `ck_users_registration_mapping_candidate`
- [X] T014 Register new model metadata, factories, Google picture claims, and dependency-safe truncation in `apps/api/migrations/env.py` and `apps/api/tests/conftest.py`
- [X] T015 Extend deny-by-default Candidate/Manager/Admin capabilities and scoped dependencies in `apps/api/app/auth/policies.py`, `apps/api/app/auth/authorization.py`, and `apps/api/app/auth/dependencies.py`
- [X] T016 Add stable feature errors, safe audit metadata, and bounded operation metrics in `apps/api/app/auth/errors.py`, `apps/api/app/auth/audit.py`, and `apps/api/app/core/observability.py`
- [X] T017 Reconcile `/auth/me`, role-transition, and `__Host-mi_session` definitions in `specs/001-user-auth/contracts/auth.openapi.yaml` and `specs/002-role-interview-management/contracts/role-interview.openapi.yaml`, then make T009 pass
- [X] T018 Add `Idempotency-Key` to the explicit credentialed CORS header allowlist in `apps/api/app/main.py` and make T010 pass
- [X] T019 Run T006–T018 against an isolated populated revision `004` PostgreSQL database and record the passing migration/foundation checkpoint in `specs/002-role-interview-management/validation.md`

**Checkpoint**: Revision `005`, common security contracts, and shared test infrastructure are ready; user-story red tests may now begin.

---

## Phase 3: User Story 1 — Authenticate and Reach the Correct Home Screen (Priority: P1) 🎯 MVP

**Goal**: Preserve Google-only authentication, route each supported role to its own home, deny cross-role routes/requests, and terminate logout sessions.

**Independent Test**: Sign in as Candidate, Manager, and Admin; verify the correct role home and direct cross-role denial; log out and prove the old session cannot reopen protected pages.

### Tests for User Story 1 — write and observe failures first

- [X] T020 [P] [US1] Write failing component tests for root role resolution, deep links, forbidden/unknown routes, history, focused headings, and logout recovery in `apps/web/src/App.test.tsx` and `apps/web/src/auth/ProtectedRoutes.test.tsx`
- [X] T021 [P] [US1] Extend failing Google-only auth, role-routing, old-session, and direct-route browser journeys in `apps/web/e2e/google-login.spec.ts`, `apps/web/e2e/role-access.spec.ts`, and `apps/web/e2e/session-lifecycle.spec.ts`
- [X] T022 [P] [US1] Extend failing backend role dependency and session-revocation regressions in `apps/api/tests/integration/test_authorization_dependencies.py`, `apps/api/tests/integration/test_global_logout.py`, and `apps/api/tests/integration/test_session_revocation.py`

### Implementation for User Story 1

- [X] T023 [P] [US1] Create focused Candidate, Manager, and Admin role-home route components in `apps/web/src/candidate/CandidateHome.tsx`, `apps/web/src/manager/ManagerHome.tsx`, and `apps/web/src/admin/AdminHome.tsx`
- [X] T024 [US1] Mount `BrowserRouter` and implement authenticated role routes, `/` resolution, `/profile` reservation, and role-safe fallback handling in `apps/web/src/main.tsx` and `apps/web/src/App.tsx`
- [X] T025 [US1] Adapt backend-aligned route guards and remove out-of-scope navigation placeholders in `apps/web/src/auth/ProtectedRoute.tsx` and `apps/web/src/navigation/RoleNavigation.tsx`
- [X] T026 [US1] Update existing strict current-user fixtures and retired role-landing assumptions in `apps/web/src/auth/RoleLanding.test.tsx`, `apps/web/src/auth/ProtectedRoutes.test.tsx`, and `apps/web/src/auth/SessionLifecycle.test.tsx`
- [X] T027 [US1] Run the targeted backend, component, and Playwright suites from T020–T026 and record the independent US1 result in `specs/002-role-interview-management/validation.md`

**Checkpoint**: All three roles authenticate, reach only their own home, and lose protected access after logout.

---

## Phase 4: User Story 2 — Manage and Use a Personal Profile (Priority: P2)

**Goal**: Show verified identity in a top-right profile disclosure and dedicated self-only profile page, with an accessible picture fallback and logout action.

**Independent Test**: Sign in with and without a usable Google picture, open the profile disclosure, verify name/email/picture or placeholder on `/profile`, then log out.

### Tests for User Story 2 — write and observe failures first

- [X] T028 [P] [US2] Write failing signed-picture validation, refresh, absent/invalid fallback, and safe-claim tests in `apps/api/tests/unit/auth/test_google_oidc.py` and `apps/api/tests/unit/auth/test_identity_binding.py`
- [X] T029 [P] [US2] Write failing `/auth/me` email/picture and self-only profile integration tests in `apps/api/tests/integration/test_admin_api_and_me.py` and `apps/api/tests/integration/test_profile_api.py`
- [X] T030 [P] [US2] Write failing strict decoder, profile image, disclosure focus/Escape/outside-close, profile page, and logout component tests in `apps/web/src/auth/AuthFlow.test.tsx`, `apps/web/src/profile/ProfilePage.test.tsx`, `apps/web/src/layout/ProfileMenu.test.tsx`, and `apps/web/src/components/ProfileImage.test.tsx`
- [X] T031 [P] [US2] Extend failing keyboard, screen-reader-name, picture-fallback, and logout browser checks in `apps/web/e2e/auth-accessibility.spec.ts` and `apps/web/e2e/google-login.spec.ts`

### Implementation for User Story 2

- [X] T032 [US2] Decode and validate the optional verified Google `picture` claim in `apps/api/app/auth/google_oidc.py`
- [X] T033 [US2] Refresh bounded name/picture identity data and expose required email/nullable picture in `apps/api/app/auth/service.py` and `apps/api/app/auth/router.py`
- [X] T034 [P] [US2] Extend strict current-user types, runtime decoding, and session-aware transport in `apps/web/src/auth/types.ts`, `apps/web/src/auth/decoders.ts`, and `apps/web/src/auth/api.ts`
- [X] T035 [P] [US2] Implement provider-image failure fallback and accessible identity rendering in `apps/web/src/components/ProfileImage.tsx`
- [X] T036 [US2] Implement the accessible top-right disclosure, focus restoration, Profile link, and Logout action in `apps/web/src/layout/ProfileMenu.tsx` and `apps/web/src/layout/AuthenticatedShell.tsx`
- [X] T037 [US2] Implement the self-only profile page and authenticated shell styling in `apps/web/src/profile/ProfilePage.tsx` and `apps/web/src/styles.css`
- [X] T038 [US2] Update all current-user browser fixtures for required email and nullable picture in `apps/web/e2e/google-login.spec.ts`, `apps/web/e2e/auth-accessibility.spec.ts`, `apps/web/e2e/session-lifecycle.spec.ts`, and `apps/web/e2e/role-access.spec.ts`
- [X] T039 [US2] Run T028–T038 with backend/component coverage and axe checks and record the independent US2 result in `specs/002-role-interview-management/validation.md`

**Checkpoint**: Every authenticated role has the same self-only, keyboard-accessible profile and logout experience.

---

## Phase 5: User Story 3 — Candidate Views Allocated Interviews (Priority: P2)

**Goal**: Give a Candidate a paginated, minimum-projection home list containing only that Candidate's scheduled interviews.

**Independent Test**: Seed different interviews for two Candidates, authenticate each in turn, and verify title/date/time/status isolation plus the empty state.

### Tests for User Story 3 — write and observe failures first

- [X] T040 [P] [US3] Write failing Candidate interview contract and malformed-response tests in `apps/api/tests/contract/test_role_interview_openapi.py` and `apps/web/src/candidate/decoders.test.ts`
- [X] T041 [P] [US3] Write failing PostgreSQL Candidate projection, pagination, empty-state, wrong-role, direct-request, and two-Candidate isolation tests in `apps/api/tests/integration/test_interview_api.py` and `apps/api/tests/integration/test_role_interview_authorization.py`
- [X] T042 [P] [US3] Write failing Candidate loading/error/retry/empty/populated/status/date/time component tests in `apps/web/src/candidate/CandidateHome.test.tsx`

### Implementation for User Story 3

- [X] T043 [P] [US3] Define Candidate interview/page schemas with minimum projections in `apps/api/app/interviews/schemas.py`
- [X] T044 [US3] Implement authenticated-Candidate-owned paginated projection queries in `apps/api/app/interviews/service.py`
- [X] T045 [US3] Expose `GET /api/v1/candidate/interviews` with Candidate authorization and safe errors in `apps/api/app/interviews/candidate_router.py` and register it in `apps/api/app/main.py`
- [X] T046 [P] [US3] Implement strict Candidate interview types, decoder, and self-scoped API client in `apps/web/src/candidate/types.ts`, `apps/web/src/candidate/decoders.ts`, and `apps/web/src/candidate/api.ts`
- [X] T047 [US3] Replace the Candidate role-home placeholder with the accessible interview table/list, time semantics, status text, async states, and retry in `apps/web/src/candidate/CandidateHome.tsx`
- [X] T048 [US3] Run T040–T047 and verify two-Candidate isolation through API and UI, then record the independent US3 result in `specs/002-role-interview-management/validation.md`

**Checkpoint**: Candidate home reveals only the authenticated Candidate's allocations and minimum JD identity.

---

## Phase 6: User Story 4 — Manager Creates and Reviews JDs (Priority: P2)

**Goal**: Let a Manager view only owned JDs and create one manually or from a safely bounded PDF, DOCX, or UTF-8 TXT upload.

**Independent Test**: Manager A creates one manual and three uploaded JDs; Manager B sees none; invalid files and CSRF failures create no row.

### Tests for User Story 4 — write and observe failures first

- [X] T049 [P] [US4] Write failing normalization and PDF/DOCX/TXT validation tests for size, signature, MIME, encryption, macros, traversal, archive bombs, binary text, blank extraction, and safe errors in `apps/api/tests/unit/jds/test_documents.py`
- [X] T050 [P] [US4] Write failing manual/upload/list, owner isolation, pagination, rollback, audit, metrics, Origin, and CSRF integration tests in `apps/api/tests/integration/test_jd_api.py` and `apps/api/tests/integration/test_role_interview_authorization.py`
- [X] T051 [P] [US4] Write failing JD OpenAPI request/response/error/multipart tests in `apps/api/tests/contract/test_role_interview_openapi.py`
- [X] T052 [P] [US4] Write failing strict decoder, owned-list, manual form, native upload, validation, double-submit, success-refresh, and error component tests in `apps/web/src/manager/decoders.test.ts`, `apps/web/src/manager/JdList.test.tsx`, and `apps/web/src/manager/JdForms.test.tsx`

### Implementation for User Story 4

- [X] T053 [US4] Implement bounded normalization and safe PDF/DOCX/TXT extraction in `apps/api/app/jds/documents.py`
- [X] T054 [P] [US4] Define strict JD pagination, manual request, multipart result, and minimum response schemas in `apps/api/app/jds/schemas.py`
- [X] T055 [US4] Implement Manager-owned JD list/manual/upload transactions, audit, and metrics in `apps/api/app/jds/service.py`
- [X] T056 [US4] Expose Manager JD GET/POST/upload endpoints with Origin/CSRF enforcement in `apps/api/app/jds/router.py` and register them in `apps/api/app/main.py`
- [X] T057 [P] [US4] Implement strict Manager JD types, runtime decoding, JSON/multipart clients, and centralized session failure handling in `apps/web/src/manager/types.ts`, `apps/web/src/manager/decoders.ts`, and `apps/web/src/manager/api.ts`
- [X] T058 [P] [US4] Implement the accessible owned-JD async list in `apps/web/src/manager/JdList.tsx`
- [X] T059 [P] [US4] Implement manual and native PDF/DOCX/TXT upload forms with field errors, in-flight guards, and live announcements in `apps/web/src/manager/JdForms.tsx`
- [X] T060 [US4] Compose the Manager JD workflow and refresh behavior in `apps/web/src/manager/ManagerHome.tsx`
- [X] T061 [US4] Run T049–T060 including hostile fixture, ownership, CSRF, and 100% targeted coverage checks and record the independent US4 result in `specs/002-role-interview-management/validation.md`

**Checkpoint**: Each Manager can safely create and see only owned JDs through both required input paths.

---

## Phase 7: User Story 5 — Manager Schedules Candidate Interviews (Priority: P2)

**Goal**: Let a Manager select an active same-organization Candidate and owned JD, schedule one future interview idempotently, and expose the same allocation only to that Manager and Candidate.

**Independent Test**: Schedule with an owned JD, replay the same key, verify one row/audit in Manager and selected Candidate lists, then exercise invalid ownership/time/resource-loss races.

**Dependencies**: Requires the US3 Candidate projection and US4 Manager JD increment for the full cross-role journey; backend scheduling tests may seed prerequisite records directly.

### Tests for User Story 5 — write and observe failures first

- [X] T062 [P] [US5] Write failing timestamp, idempotency digest/fingerprint, replay, and conflict unit tests in `apps/api/tests/unit/interviews/test_scheduling.py`
- [X] T063 [P] [US5] Write failing Candidate selector, scheduling/list, atomic audit, invalid resource/time, retry, and cross-role projection integration tests in `apps/api/tests/integration/test_interview_api.py` and `apps/api/tests/integration/test_schedule_idempotency.py`
- [X] T064 [P] [US5] Write failing two-session PostgreSQL barrier tests for both lock orders against Candidate/Manager role/status loss and JD owner/tenant change in `apps/api/tests/integration/test_scheduling_resource_races.py`
- [X] T065 [P] [US5] Write failing tenant participant success/block/failure-rollback and registry-completeness tests in `apps/api/tests/unit/interviews/test_tenancy.py` and `apps/api/tests/integration/test_role_change_interview_consistency.py`
- [X] T066 [P] [US5] Write failing Manager Candidate/interview decoder, schedule form, idempotency, async list, validation, and double-submit component tests in `apps/web/src/manager/decoders.test.ts`, `apps/web/src/manager/ScheduleInterviewForm.test.tsx`, and `apps/web/src/manager/ScheduledInterviewList.test.tsx`

### Implementation for User Story 5

- [X] T067 [P] [US5] Add Manager Candidate, schedule request, Manager interview, pagination, and replay schemas in `apps/api/app/interviews/schemas.py`
- [X] T068 [US5] Implement deterministic locking, active-resource revalidation, future-time validation, scoped idempotency, one-row allocation, audit, and Manager/Candidate projections in `apps/api/app/interviews/service.py`
- [X] T069 [US5] Expose Manager Candidate GET and interview GET/POST routes with Origin/CSRF/idempotency handling in `apps/api/app/interviews/manager_router.py` and register them in `apps/api/app/main.py`
- [X] T070 [US5] Implement the fail-closed multi-owner scheduled-interview migration participant in `apps/api/app/interviews/tenancy.py` and register it once in `apps/api/app/main.py`
- [X] T071 [P] [US5] Extend strict Manager Candidate/interview types, decoders, and API methods in `apps/web/src/manager/types.ts`, `apps/web/src/manager/decoders.ts`, and `apps/web/src/manager/api.ts`
- [X] T072 [P] [US5] Implement the Candidate/JD/date/time scheduling form with offset-aware conversion, per-intent UUID keys, retry semantics, errors, and live success in `apps/web/src/manager/ScheduleInterviewForm.tsx`
- [X] T073 [P] [US5] Implement the scheduling Manager's paginated interview history in `apps/web/src/manager/ScheduledInterviewList.tsx`
- [X] T074 [US5] Compose scheduling, Candidate choices, owned JDs, history refresh, and Candidate allocation refresh behavior in `apps/web/src/manager/ManagerHome.tsx` and `apps/web/src/candidate/CandidateHome.tsx`
- [X] T075 [US5] Run T062–T074 including both concurrency lock orders and exact one-row/one-audit visibility, then record the independent US5 result in `specs/002-role-interview-management/validation.md`

**Checkpoint**: Scheduling is atomic, idempotent, ownership-safe, and visible to exactly the scheduling Manager and selected Candidate.

---

## Phase 8: User Story 6 — Admin Reviews Users and JDs (Priority: P2)

**Goal**: Give Admins application-wide independently paginated user/JD tables, accessible user details, and all supported role transitions while denying non-Admins.

**Independent Test**: Traverse unchanged 1,000-user/JD datasets exactly once, inspect a user, change through supported roles, verify session revocation and routing, and prove Candidate/Manager denial.

### Tests for User Story 6 — write and observe failures first

- [X] T076 [P] [US6] Write failing application-wide user/JD pagination, stable-order, changing-dataset, minimum-projection, detail, authorization, and 1,000-record tests in `apps/api/tests/integration/test_admin_pagination.py` and `apps/api/tests/integration/test_role_interview_authorization.py`
- [X] T077 [P] [US6] Replace obsolete CandidateProfile-conflict expectations with failing all-role transition, provenance/profile retention, CandidateProfile creation, no-op, generation, audit, and session-revocation tests in `apps/api/tests/integration/test_admin_user_mutations.py`
- [X] T078 [P] [US6] Write failing Admin list/detail/role OpenAPI tests in `apps/api/tests/contract/test_role_interview_openapi.py` and `apps/api/tests/contract/test_auth_openapi.py`
- [X] T079 [P] [US6] Write failing strict Admin decoder, independent URL pager, semantic tables, dialog focus/Escape/restore, role save, async states, and denial component tests in `apps/web/src/admin/decoders.test.ts`, `apps/web/src/admin/AdminHome.test.tsx`, `apps/web/src/admin/UsersTable.test.tsx`, `apps/web/src/admin/JdsTable.test.tsx`, and `apps/web/src/admin/UserDetailsDialog.test.tsx`

### Implementation for User Story 6

- [X] T080 [US6] Implement application-wide minimum user/JD pagination, user detail, and provenance-preserving all-role transitions in `apps/api/app/admin/service.py`
- [X] T081 [US6] Expose Admin user list/detail/role and JD list endpoints with existing Admin/CSRF guards in `apps/api/app/admin/router.py`
- [X] T082 [P] [US6] Implement strict Admin projections, page decoders, and API clients in `apps/web/src/admin/types.ts`, `apps/web/src/admin/decoders.ts`, and `apps/web/src/admin/api.ts`
- [X] T083 [P] [US6] Implement reusable semantic pagination with boundary states and URL synchronization in `apps/web/src/components/Pagination.tsx`
- [X] T084 [P] [US6] Implement the semantic users and JDs tables with minimum columns and keyboard-operable details controls in `apps/web/src/admin/UsersTable.tsx` and `apps/web/src/admin/JdsTable.tsx`
- [X] T085 [US6] Implement the native accessible user detail dialog, supported-role save, announcements, Escape, and focus restoration in `apps/web/src/admin/UserDetailsDialog.tsx`
- [X] T086 [US6] Compose independent `usersPage`/`jdsPage` state, loading/error/empty states, detail refresh, and role updates in `apps/web/src/admin/AdminHome.tsx`
- [X] T087 [US6] Run T076–T086 over seeded 1,000-record unchanged and changing datasets and record the independent US6 result in `specs/002-role-interview-management/validation.md`

**Checkpoint**: Admin operations are complete, paginated, accessible, and unavailable to Candidate and Manager sessions.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Prove integrated journeys, accessibility, privacy, performance, recovery, and exact coverage after all desired stories are complete.

- [X] T088 [P] Add shared async, status, and accessibility primitives with exhaustive tests in `apps/web/src/components/AsyncState.tsx`, `apps/web/src/components/StatusBadge.tsx`, `apps/web/src/components/AsyncState.test.tsx`, and `apps/web/src/components/StatusBadge.test.tsx`
- [X] T089 [P] Extract the axe helper and write failing integrated role/profile/JD/scheduling/Admin keyboard journeys in `apps/web/e2e/support/accessibility.ts`, `apps/web/e2e/role-interview-management.spec.ts`, and `apps/web/e2e/role-interview-accessibility.spec.ts`
- [X] T090 Implement responsive WCAG 2.2 AA focus, contrast, target-size, reduced-motion, scrollable-table, disclosure, form, and dialog styling in `apps/web/src/styles.css` and make T089 pass
- [X] T091 [P] Add deterministic 1,000-user/JD/session seed generation and backend baseline measurements in `apps/api/scripts/seed_role_interview_performance.py` and `apps/api/scripts/role_interview_baseline.py`
- [X] T092 [P] Write production-preview proxy/config tests in `apps/web/src/viteConfig.test.ts` and implement the isolated performance configuration in `apps/web/playwright.performance.config.ts`
- [X] T093 [P] Implement at least 100 authenticated 10-context rendered-page measurements and SC-004 assertions in `apps/web/performance/role-interview-performance.spec.ts`
- [X] T094 Implement the exact-database guard, maintenance connection, complete test settings, browser dependencies, migration/seed/API/preview health lifecycle, restricted state, and cleanup trap in `scripts/run-role-interview-performance.sh`
- [X] T095 [P] Complete the named upload/profile/scheduling security and privacy review with safe audit/log/telemetry evidence in `specs/002-role-interview-management/security-privacy-review.md`
- [ ] T096 [P] Complete keyboard, responsive, axe, NVDA/VoiceOver, focus, dialog, and live-region evidence in `specs/002-role-interview-management/accessibility-validation.md`
- [ ] T097 [P] Execute and record the 20-participant first-attempt, primary-task, separate manual/upload, scheduling, and Admin timing protocol in `specs/002-role-interview-management/usability-validation.md`
- [X] T098 Run populated `004→005`, guarded isolated `005→004→005`, participant rollback, and forward-recovery validation and record evidence in `specs/002-role-interview-management/validation.md`
- [X] T099 Run `apps/api/scripts/role_interview_baseline.py` and `scripts/run-role-interview-performance.sh`, verify privacy and SC-004 thresholds, and record p50/p95/max/failures/environment in `specs/002-role-interview-management/validation.md`
- [X] T100 Close every backend/frontend line, branch, function, and statement gap and run the isolated full blocking gate from `scripts/quality-gate.sh` using `.coverage-thresholds.json`
- [ ] T101 Re-run every scenario in `specs/002-role-interview-management/quickstart.md`, complete FR-001–FR-034 and SC-001–SC-011 traceability, and sign off `specs/002-role-interview-management/validation.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Starts immediately; T001 must finish before parser implementation, while T002–T004 are parallel-safe.
- **Foundational (Phase 2)**: Depends on Setup and blocks every user story. Tests T006–T010 must fail first; T011–T018 implement the foundation; T019 is its gate.
- **US1 (Phase 3)**: Depends only on the Foundational checkpoint and is the MVP.
- **US2 (Phase 4)**: Depends on the US1 authenticated route shell for its shared header and `/profile` route.
- **US3 (Phase 5)**: Depends on Foundational; seeded interviews make it independently testable without scheduling UI.
- **US4 (Phase 6)**: Depends on Foundational and T001; it is independently testable with two Manager sessions.
- **US5 (Phase 7)**: Depends on US3 and US4 for the complete Manager-to-Candidate journey; its backend services remain testable with seeded prerequisites.
- **US6 (Phase 8)**: Depends on Foundational and US1 routing; seeded JDs make it independent of US4 implementation.
- **Polish (Phase 9)**: Depends on every story selected for release; T100 and T101 are the final blocking gates.

### User Story Completion Order

```text
Setup → Foundation → US1 (MVP) → US2
                   ├──────────→ US3 ─┐
                   ├──────────→ US4 ─┼→ US5
                   └──────────→ US6 ─┘
All selected stories → Integrated accessibility/performance/release gate
```

### Within Each User Story

1. Complete every listed test task and observe the intended failure.
2. Implement models/schemas before services, services before routes, and transports before screens.
3. Make targeted unit/contract/integration/component tests pass.
4. Run the story's independent checkpoint before starting a dependent story.
5. Preserve server-side role/organization/ownership checks even when the frontend hides a route.

## Parallel Opportunities

- T002–T004 can run in parallel after dependency review begins.
- T006–T010 are separate red-test files and can run in parallel.
- After Foundation, US3 and US4 can proceed in parallel with US1/US2 work; US6 can proceed once US1 routing is stable.
- Within each story, test tasks marked `[P]` can be authored concurrently before implementation.
- Backend schemas, frontend types/decoders, and isolated UI primitives marked `[P]` can run concurrently where they do not share files.
- T089, T091–T093, and T095–T097 can proceed in parallel after their underlying stories are complete.

## Parallel Example: User Story 4

```text
Task T049: JD document parser red tests in apps/api/tests/unit/jds/test_documents.py
Task T050: JD API/authorization red tests in apps/api/tests/integration/test_jd_api.py
Task T051: JD OpenAPI red tests in apps/api/tests/contract/test_role_interview_openapi.py
Task T052: Manager JD frontend red tests in apps/web/src/manager/*.test.ts(x)

After those failures are confirmed:
Task T054: JD schemas in apps/api/app/jds/schemas.py
Task T057: Manager JD frontend transport in apps/web/src/manager/{types,decoders,api}.ts
Task T058: Owned JD list in apps/web/src/manager/JdList.tsx
Task T059: Manual/upload forms in apps/web/src/manager/JdForms.tsx
```

## Parallel Example: User Story 6

```text
Task T076: Admin pagination/API red tests
Task T077: Admin all-role-transition red tests
Task T078: Admin contract red tests
Task T079: Admin decoder/table/dialog red tests

After backend contracts stabilize:
Task T082: Admin frontend transport
Task T083: Reusable pagination control
Task T084: Users and JDs tables
```

## Implementation Strategy

### MVP First

1. Complete Setup and Foundation.
2. Complete US1 using strict red-green TDD.
3. Stop and run the US1 independent checkpoint.
4. Demonstrate Google-only login, correct role routing, direct cross-role denial, and logout session termination.

### Incremental Delivery

1. Add US2 for the shared identity/profile experience.
2. Add US3 and US4 independently for Candidate visibility and Manager JD ownership.
3. Add US5 to connect owned JDs to Candidate allocations atomically.
4. Add US6 for application-wide Admin operations.
5. Complete integrated accessibility, security/privacy, performance, usability, migration, and 100% coverage gates.

### Delivery Discipline

- Never implement before the matching red test fails for the intended reason.
- Commit after each task or coherent red-green unit; never bypass hooks with `--no-verify`.
- Keep uploaded originals, filenames, raw idempotency keys, emails, picture URLs, and JD text out of logs/audits.
- Treat `validation.md` as evidence, not a substitute for automated assertions.
- Stop at any story checkpoint to validate or demonstrate that increment independently.

## Notes

- `[P]` means file ownership and dependency ordering make concurrent execution safe.
- Story labels provide FR/SC traceability; Setup, Foundation, and Polish intentionally have no story label.
- The existing feature OpenAPI artifact is updated in place; runtime/generated contract checks must remain equivalent.
- Manual screen-reader and participant studies are release tasks because automation cannot supply those outcomes.
- Any missed security, accessibility, performance, usability, migration, or exact coverage gate blocks completion.
