# Tasks: Candidate Self-Registration and Organization Domain Mapping

**Input**: Approved design artifacts in `/specs/001-user-auth/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`

**Tests**: Mandatory. For every test task, write the test, run it, and preserve evidence that it failed for the intended missing behavior before starting its paired implementation task. The blocking coverage thresholds are the values in `.coverage-thresholds.json`.

**Scope**: This backlog is the remaining delta after the existing Google-only authentication foundation. It adds controlled Candidate self-registration, Admin mapping APIs, atomic mapping lifecycle operations, absolute frontend callback redirects, and the required regression evidence without rebuilding completed authentication work.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it targets separate files and has no dependency on another incomplete task in the same phase
- **[Story]**: Maps the task to a user story in `spec.md`
- Every checklist item includes an exact repository file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the migration baseline and prepare the narrow module/test structure required by the approved design.

- [X] T001 Record the current Alembic head, revision `001` constraint names, active coverage commands, and red-green evidence convention in `specs/001-user-auth/validation.md`
- [X] T002 [P] Create the typed tenancy package skeleton in `apps/api/app/tenancy/__init__.py`, `apps/api/app/tenancy/contracts.py`, and `apps/api/app/tenancy/coordinator.py`
- [X] T003 [P] Add documented frontend application origin and optional development domain-mapping seed examples without secrets in `.env.example`

**Checkpoint**: The existing schema baseline is captured and all new implementation locations are explicit.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish schema, canonical identifiers, transaction coordination, validated configuration, and deterministic fixtures used by every story.

**Critical**: No user-story implementation starts until this phase is green.

### Foundational tests — write and run first

- [X] T004 [P] Add failing populated-revision migration tests for `001 -> 002`, nullable provenance, partial active-domain uniqueness, revocation checks, `ON UPDATE CASCADE`, downgrade/re-upgrade, and collision rollback in `apps/api/tests/integration/test_auth_schema.py`
- [X] T005 [P] Add failing unit tests for email validation plus exact ASCII/IDNA domain canonicalization and rejection of URLs, wildcards, `@`, trailing dots, invalid labels, and implicit subdomain matches in `apps/api/tests/unit/auth/test_identifiers.py`
- [X] T006 [P] Add failing unit tests for participant name uniqueness, deterministic ordering, supplied-session use, prohibited transaction control, success counts, and injected-failure rollback in `apps/api/tests/unit/tenancy/test_coordinator.py`
- [X] T007 [P] Add failing configuration tests for a validated frontend application origin, allowed-origin membership, production HTTPS, and unsafe origin rejection in `apps/api/tests/unit/core/test_config.py`

### Foundational implementation

- [X] T008 Implement forward revision `002` with `organization_domain_mappings`, nullable immutable User provenance, mapping revocation reasons, named indexes/checks, and cascading composite tenant FKs in `apps/api/migrations/versions/002_add_candidate_self_registration.py`
- [X] T009 Implement `OrganizationDomainMapping`, registration provenance, relationships, checks, and new audit/session enums in `apps/api/app/auth/models.py`
- [X] T010 [P] Implement shared validated email, local-part, display-name, and exact domain canonicalization helpers in `apps/api/app/auth/identifiers.py`
- [X] T011 Implement the typed same-transaction participant registry, validation/lock phase, migration phase, deterministic ordering, and fail-closed coordinator in `apps/api/app/tenancy/contracts.py` and `apps/api/app/tenancy/coordinator.py`
- [X] T012 Update PostgreSQL cleanup order, factories, fake Google claims, mapping builders, and synthetic participant fixtures for revision `002` in `apps/api/tests/conftest.py`
- [X] T013 Implement validated frontend application-origin settings and add `DELETE` to credentialed CORS methods in `apps/api/app/core/config.py` and `apps/api/app/main.py`

**Checkpoint**: Revision `002`, canonical domain logic, transaction participants, frontend-origin validation, and fixtures pass independently.

---

## Phase 3: User Story 1 - Sign In with Google (Priority: P1) — MVP

**Goal**: Preserve unbound pre-provisioned identity binding, and otherwise register a verified exact-domain user atomically as an active Candidate; let Admins manage mappings safely, including atomic removal and reassignment.

**Independent Test**: Against PostgreSQL and the deterministic signed OIDC fake, prove mapped first login creates exactly one Candidate/profile/identity/session/provenance set, unmapped login leaves no partial rows, pre-provisioned binding remains mapping-independent, mapping lifecycle operations affect only provenance-linked Candidates, and every race or injected migration failure ends in one complete state.

### Tests for User Story 1 — write and run first

- [X] T014 [P] [US1] Add failing signed-claim tests for validated Google `name`, Unicode/whitespace normalization, malformed/control/overlength fallback, validated email, and invalid-email denial in `apps/api/tests/unit/auth/test_google_oidc.py`
- [X] T015 [P] [US1] Add failing identity-resolution tests for pre-provision precedence, mapped Candidate creation inputs, ambiguous global pre-provision matches, exact-domain denial, removed mappings, and subject/email collisions in `apps/api/tests/unit/auth/test_identity_binding.py`
- [X] T016 [P] [US1] Add failing callback tests for atomic mapped registration, Candidate-only role, one profile/identity/session/audit, case-insensitive exact matching, provider/flush rollback, idempotent subject replay, and zero partial rows on denial in `apps/api/tests/integration/test_google_callback.py`
- [X] T017 [P] [US1] Add failing OpenAPI contract assertions for mapping list/create/reassign/remove schemas, status codes, stable errors, Admin security, mutation CSRF/Origin inputs, and absence of role selection in `apps/api/tests/contract/test_auth_openapi.py`
- [X] T018 [P] [US1] Add failing Admin API tests for normalized create/list, active uniqueness, inactive/missing organization errors, soft removal, terminal removed rows, same-org reassignment no-op, and safe response envelopes in `apps/api/tests/integration/test_organization_domain_mappings.py`
- [X] T019 [P] [US1] Add failing lifecycle tests proving removal disables only provenance-linked Candidates and reassignment migrates User/Profile/Identity/Session tenant columns, preserves historical audit rows and pre-provisioned users, revokes sessions, and rolls back on target-email or participant failure in `apps/api/tests/integration/test_domain_mapping_lifecycle.py`
- [X] T020 [P] [US1] Add failing two-connection PostgreSQL barrier tests for create/register, remove/register, and reassign/register lock ordering with bounded lock and statement timeouts in `apps/api/tests/integration/test_domain_mapping_concurrency.py`
- [X] T021 [P] [US1] Add failing callback redirect tests for configured absolute frontend success/error URLs, allowlisted relative return paths, safe query keys, and Host/Forwarded open-redirect resistance in `apps/api/tests/integration/test_google_callback.py`
- [X] T022 [P] [US1] Add failing frontend tests for allowlisted callback-error parsing, contact-Admin/retry recovery, correlation display policy, focus, live-region announcements, and protected-state clearing in `apps/web/src/auth/AuthFlow.test.tsx`
- [X] T023 [P] [US1] Add failing Playwright journeys for mapped Candidate onboarding, unmapped recovery, old-cookie denial after reassignment, and fresh login into the target organization in `apps/web/e2e/google-login.spec.ts`

### Implementation for User Story 1

- [X] T024 [P] [US1] Extend verified Google claims with optional signed `name`, validated email normalization, safe display-name fallback, and provider-response error mapping in `apps/api/app/auth/google_oidc.py`
- [X] T025 [US1] Implement advisory-domain locking, pre-provision-first binding, mapping recheck, atomic Candidate/profile/identity creation, immutable provenance, and concurrent subject idempotency in `apps/api/app/auth/service.py`
- [X] T026 [US1] Implement normalized mapping create/list plus locked soft-removal and reassignment orchestration, target collision preflight, Candidate generation changes, participant invocation, and same-org no-op in `apps/api/app/admin/service.py`
- [X] T027 [US1] Implement strict camelCase mapping request/response models and Admin-only GET/POST/PATCH/DELETE routes with exact CSRF/Origin enforcement in `apps/api/app/admin/router.py`
- [X] T028 [US1] Add mapping lifecycle, Candidate self-registration, organization-change, revocation, and rollback-safe audit helpers with allowlisted metadata in `apps/api/app/auth/audit.py`
- [X] T029 [US1] Implement mapping-specific session revocation and generation handling while retaining revoked session tenant consistency in `apps/api/app/auth/sessions.py`
- [X] T030 [US1] Build configured absolute frontend redirects for success and safe callback errors without trusting request host headers in `apps/api/app/auth/router.py`
- [X] T031 [US1] Wire the mapping routes and explicit production participant registry into application composition in `apps/api/app/main.py`
- [X] T032 [US1] Implement typed callback-error decoding, accessible local recovery copy, and authenticated-state reset in `apps/web/src/auth/AuthProvider.tsx`, `apps/web/src/auth/types.ts`, and `apps/web/src/auth/decoders.ts`
- [X] T033 [P] [US1] Add idempotent `--domain-mapping domain:org-slug` development seeding with canonical validation and no production identities in `apps/api/scripts/seed_auth.py`

**Checkpoint**: User Story 1 independently delivers the controlled Candidate-registration and complete mapping-lifecycle MVP.

---

## Phase 4: User Story 2 - Enforce Role Permissions (Priority: P1)

**Goal**: Ensure mapping administration remains Admin-only and a self-registered Candidate gains no capability outside the existing Candidate ownership policy.

**Independent Test**: Exercise mapping routes and protected-resource fixtures as anonymous, Candidate, Manager, and Admin users across organizations; only Admin mapping operations and the already-authorized role/resource combinations succeed, with safe audited denials.

### Tests for User Story 2 — write and run first

- [X] T034 [P] [US2] Add failing policy tests for the mapping-management capability, Candidate default-role boundaries, organization equality, and deny-by-default missing scope in `apps/api/tests/unit/auth/test_policies.py`
- [X] T035 [P] [US2] Add failing integration tests proving anonymous requests return 401 and Candidate/Manager or cross-origin mapping mutations return safe 403 without state change in `apps/api/tests/integration/test_organization_domain_mappings.py`
- [X] T036 [P] [US2] Add failing tests for safe audited non-Admin mapping mutation denials that survive the denied request transaction in `apps/api/tests/unit/auth/test_audit.py`

### Implementation for User Story 2

- [X] T037 [US2] Add the Admin-only organization-domain-mapping capability and preserve Candidate/Manager ownership scopes in `apps/api/app/auth/policies.py`
- [X] T038 [US2] Enforce the mapping capability through reusable authenticated dependencies and a denial-audit boundary that cannot grant or leak access in `apps/api/app/auth/dependencies.py` and `apps/api/app/admin/router.py`

**Checkpoint**: User Story 2 independently proves the new registration path does not broaden role or tenant authority.

---

## Phase 5: User Story 3 - End and Govern Sessions (Priority: P2)

**Goal**: Mapping removal and reassignment end every affected session, invalidate old cookies, and require fresh authentication with safe recovery guidance.

**Independent Test**: Create multiple sessions per mapped Candidate, remove or reassign the mapping, and prove every old session is explicitly revoked and denied while unaffected users remain active; after reassignment a fresh login resolves only the target organization.

### Tests for User Story 3 — write and run first

- [X] T039 [P] [US3] Add failing unit tests for `DOMAIN_MAPPING_REMOVED` and `DOMAIN_MAPPING_REASSIGNED`, all-session revocation, generation mismatch, and already-revoked history in `apps/api/tests/unit/auth/test_sessions.py`
- [X] T040 [P] [US3] Add failing multi-session integration tests for old-cookie denial, unaffected-user continuity, safe recovery codes, and fresh post-reassignment login in `apps/api/tests/integration/test_session_revocation.py`
- [X] T041 [P] [US3] Add failing browser tests for callback error recovery and session-expired focus/state clearing after mapping lifecycle changes in `apps/web/src/auth/SessionLifecycle.test.tsx`

### Implementation for User Story 3

- [X] T042 [US3] Complete dependency-time denial and safe recovery mapping for mapping-revoked or generation-stale sessions in `apps/api/app/auth/dependencies.py` and `apps/api/app/auth/errors.py`
- [X] T043 [US3] Complete accessible frontend recovery and sign-in-again behavior for mapping lifecycle session loss in `apps/web/src/auth/SessionExpiredPage.tsx` and `apps/web/src/auth/AuthProvider.tsx`

**Checkpoint**: User Story 3 independently proves no affected session survives removal or reassignment.

---

## Phase 6: User Story 4 - Use Google-Only Authentication (Priority: P3)

**Goal**: Permit controlled Candidate creation only inside the Google callback while retaining zero password, public organization, role-selection, or standalone registration surface.

**Independent Test**: Inspect executable OpenAPI, FastAPI routes, rendered views, and browser navigation; the mapped Google callback works, but no password route, registration form, organization picker, or role picker exists.

### Tests for User Story 4 — write and run first

- [X] T044 [P] [US4] Revise failing backend absence tests to permit callback-owned Candidate creation while forbidding password, public registration, organization selection, and role selection routes in `apps/api/tests/contract/test_google_only_auth.py`
- [X] T045 [P] [US4] Add failing frontend assertions that mapped onboarding still exposes only Google sign-in and no password, registration, organization, or role controls in `apps/web/src/auth/GoogleOnlyAuth.test.tsx`

### Implementation for User Story 4

- [X] T046 [US4] Align the executable Google-only contract and frontend login copy with callback-controlled Candidate self-registration in `specs/001-user-auth/contracts/auth.openapi.yaml` and `apps/web/src/auth/LoginPage.tsx`

**Checkpoint**: User Story 4 independently proves self-registration introduced no unsupported credential or role-selection surface.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Close documentation, security, accessibility, performance, traceability, and blocking quality evidence for the complete feature.

- [X] T047 [P] Update local OAuth, frontend-origin, revision `002`, domain seed, Admin mapping lifecycle, rollback, and incident recovery instructions in `docs/authentication.md` and `Readme.md`
- [X] T048 [P] Extend automated accessibility coverage for unmapped-domain, provider-error, revoked-session, and fresh-sign-in journeys in `apps/web/e2e/auth-accessibility.spec.ts`
- [ ] T049 [P] Execute and record manual keyboard plus NVDA/VoiceOver checks for the new error and recovery states in `specs/001-user-auth/accessibility-validation.md`
- [X] T050 [P] Update the named security/privacy review for domain spoofing, IDNA, advisory locks, CSRF, open redirects, tenant migration, provenance, audit privacy, and participant failure in `specs/001-user-auth/security-privacy-review.md`
- [X] T051 [P] Extend the non-blocking authentication baseline with mapped first-login and known-login request mixes and record environment, correctness, throughput, p50, and p95 in `apps/api/scripts/auth_baseline.py` and `specs/001-user-auth/performance/baseline.json`
- [X] T052 [P] Map FR-001 through FR-017, SC-001 through SC-011, all clarified acceptance scenarios, and explicit non-goals to code and evidence in `specs/001-user-auth/traceability.md`
- [X] T053 Run Ruff, mypy, PostgreSQL pytest with coverage, Vitest coverage, Playwright, Alembic upgrade/downgrade checks, and `bash scripts/quality-gate.sh`, recording exact results in `specs/001-user-auth/validation.md`
- [X] T054 Execute every runnable scenario in `specs/001-user-auth/quickstart.md` and record any staging-only or manual evidence in `specs/001-user-auth/validation.md`
- [X] T055 Run Spec Kit consistency analysis and convergence, resolve all findings within the approved scope, and record the clean result in `specs/001-user-auth/validation.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Starts immediately; T001 records the baseline before any schema work.
- **Foundational (Phase 2)**: Depends on Setup and blocks every story. T004-T007 must produce intended red tests before T008-T013.
- **US1 (Phase 3)**: Depends on Foundational and is the feature MVP.
- **US2 (Phase 4)**: Depends on the US1 mapping endpoints but remains independently verifiable through authorization fixtures.
- **US3 (Phase 5)**: Depends on US1 removal/reassignment and session revocation behavior.
- **US4 (Phase 6)**: Depends on stable US1 routes and can otherwise proceed alongside US2 or US3.
- **Polish (Phase 7)**: Documentation tasks may begin after their contracts stabilize; T053-T055 require all selected story phases.

### User Story Completion Order

```text
Setup -> Foundational -> US1 (MVP) -> US2 -> US3 -> Polish
                         |             |      |
                         +-----------> US4 ---+
```

### Within Each Story

- Write and run the listed tests first; confirm each fails for the intended missing behavior.
- Implement persistence and validation before services, services before routes, and backend contracts before frontend integration.
- Run the story-specific unit, contract, integration, and browser checks at its checkpoint.
- Preserve one PostgreSQL transaction for mapping/core/participant/audit changes; no participant may commit, roll back, or perform external I/O.

## Parallel Opportunities

- Setup tasks T002-T003 target independent files after T001.
- Foundational tests T004-T007 can be authored concurrently; T010 can proceed separately from T008-T009 after its test exists.
- US1 test tasks T014-T023 target distinct unit, contract, integration, frontend, and browser concerns; T024 and T033 target independent implementation files.
- US2 tests T034-T036 can run concurrently before T037-T038.
- US3 tests T039-T041 can run concurrently before T042-T043.
- US4 tests T044-T045 can run concurrently before T046.
- Polish tasks T047-T052 can proceed in parallel once their corresponding behavior is stable.

## Parallel Execution Examples

### User Story 1

```text
T014: OIDC name/email tests in apps/api/tests/unit/auth/test_google_oidc.py
T017: Mapping contract tests in apps/api/tests/contract/test_auth_openapi.py
T018: Admin mapping API tests in apps/api/tests/integration/test_organization_domain_mappings.py
T020: PostgreSQL race tests in apps/api/tests/integration/test_domain_mapping_concurrency.py
T022-T023: Frontend unit and browser journeys in apps/web/
```

### User Story 2

```text
T034: Capability tests in apps/api/tests/unit/auth/test_policies.py
T035: Route authorization tests in apps/api/tests/integration/test_organization_domain_mappings.py
T036: Denial-audit tests in apps/api/tests/unit/auth/test_audit.py
```

### User Story 3

```text
T039: Revocation unit tests in apps/api/tests/unit/auth/test_sessions.py
T040: Multi-session integration tests in apps/api/tests/integration/test_session_revocation.py
T041: Browser-state tests in apps/web/src/auth/SessionLifecycle.test.tsx
```

### User Story 4

```text
T044: Backend route-absence contract in apps/api/tests/contract/test_google_only_auth.py
T045: Frontend surface-absence assertions in apps/web/src/auth/GoogleOnlyAuth.test.tsx
```

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational with migration recovery and transaction tests green.
2. Complete US1 using red-green-refactor TDD.
3. Stop and validate mapped registration, unmapped denial, pre-provision precedence, Admin lifecycle operations, atomic rollback, and concurrency independently.

### Incremental Delivery

1. **US1**: Controlled Google Candidate registration and full mapping lifecycle.
2. **US2**: Admin-only management and unchanged Candidate/Manager authorization boundaries.
3. **US3**: Complete revocation and fresh-login behavior for mapping mutations.
4. **US4**: Executable proof that Google remains the only authentication surface.
5. **Polish**: Accessibility, security/privacy, performance baseline, traceability, and the blocking 100% quality gate.

## Notes

- `[P]` means separate files and no dependency on another incomplete task in that phase; shared files such as `auth/service.py`, `admin/service.py`, `auth/router.py`, and `AuthProvider.tsx` remain sequential.
- Existing revision `001` is immutable; all schema changes belong in revision `002`.
- Historical `AuditEvent` rows retain their original organization and are never tenant-migrated.
- Removed mapping rows are terminal provenance records; recreating the same domain creates a new mapping incarnation.
- No Admin mapping UI, downstream interview/report implementation, Redis, distributed transaction, password flow, public organization creation, or new dependency is in scope.
- Never use live Google in routine tests, embed secrets/production identities, bypass Git hooks, or weaken `.coverage-thresholds.json`.
