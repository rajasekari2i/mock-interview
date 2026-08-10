# Validation Evidence: Role-Based Interview Management

## Foundation checkpoint — 2026-08-10

- Dependency license review: passed for 43 direct dependencies.
- Parser fixtures: generated PDF and DOCX fixtures were parsed successfully; originals contain no
  confidential content.
- Migration URL precedence, schema metadata, capability/error/audit/metrics, OpenAPI equivalence,
  and credentialed CORS focused suite: 39 passed.
- Populated PostgreSQL revision `004→005`, schema round-trip, and audit suite: 9 passed against the
  disposable `mockinterview_role_interview_test` database; the database was dropped afterward.
- Full backend regression suite: 223 passed against the disposable database.
- Frontend regression suite: 30 passed; strict TypeScript and ESLint passed.
- Ruff and strict mypy passed for the foundation source.

This checkpoint validates T001–T019 only. Story, accessibility, usability, performance, full
coverage, and final traceability evidence will be appended as their phases complete.

## US1 checkpoint — 2026-08-10

- New route tests were observed failing for cross-role and unknown saved paths before routing was
  implemented.
- Role routing component suite: 19 passed; full frontend regression suite: 33 passed.
- Google login, role access, and session lifecycle browser suite: 8 passed after updating the
  saved-route expectation.
- Backend role dependency, global logout, and session-revocation suite: 8 passed against the
  disposable PostgreSQL database, which was dropped afterward.
- Production frontend build, strict TypeScript, ESLint, Ruff, and strict mypy passed.

US1 independently demonstrates Google-only session reuse, Candidate/Manager/Admin home routing,
direct cross-role denial, role-safe unknown-route recovery, and old-session rejection after logout.

## US2 checkpoint — 2026-08-10

- Signed-picture and identity-refresh tests were observed failing before implementation; malformed optional picture claims now degrade safely to a local placeholder.
- Backend: 238 tests passed against a migrated disposable PostgreSQL database with exact 100% line and branch coverage; the database was dropped afterward.
- Frontend: 40 component tests passed with exact 100% lines, branches, functions, and statements.
- Browser: 12 affected Google login, profile, keyboard, session, and role-access journeys passed, including open-menu axe checks.
- Strict TypeScript and ESLint passed.

US2 exposes only the authenticated user's verified name, email, and nullable picture through `/auth/me`; the shared profile disclosure and page are keyboard-operable for every role.

## US3 checkpoint — 2026-08-10

- Candidate endpoint and UI tests were observed failing before implementation.
- Candidate API/contract suite: 6 passed against a disposable migrated PostgreSQL database, including a second Candidate whose allocation never appeared; the database was dropped afterward.
- Frontend suite remains at exact 100% lines, branches, functions, and statements with loading, failure/retry, empty, and populated states covered.
- The response contains only interview ID, JD ID/title, scheduled instant, and textual status; no candidate selector or candidate ID is accepted from the client.

US3 independently proves authenticated-Candidate ownership filtering, stable time ordering, pagination metadata, UTC date/time semantics, and safe wrong-role denial.

## US4 checkpoint — 2026-08-10

- JD parser and API tests were observed failing before implementation.
- Backend targeted suite: 32 tests passed against a migrated disposable PostgreSQL database with exact 100% line and branch coverage; the database was dropped afterward.
- Contract suite: 6 tests passed, including owned pagination, JSON mutation, multipart upload, CSRF headers, size limit, and safe error responses.
- Frontend: 52 component tests passed with exact 100% lines, branches, functions, and statements.
- Ruff and strict mypy passed for the affected backend source.

US4 independently proves Manager-owned manual and PDF/DOCX/UTF-8 TXT JD creation, safe bounded extraction, CSRF enforcement, invalid-upload rollback, explicit async states, duplicate-submit guards, and cross-Manager isolation.

## US5 checkpoint — 2026-08-10

- Scheduling helper, API, tenant participant, and UI tests were observed failing before implementation.
- Backend focused suite: 25 unit, integration, participant, and contract tests passed against a migrated disposable PostgreSQL database.
- Six real two-connection PostgreSQL race cases passed: Candidate, Manager, and owned-JD loss in both mutation-first and scheduling-first lock orders.
- Full backend regression: 289 tests passed with exact 100% line and branch coverage before the six race cases were added; the disposable database was dropped afterward.
- Frontend: 59 component tests passed with exact 100% lines, branches, functions, and statements; strict TypeScript, ESLint, Ruff, and mypy passed.

US5 proves future offset-aware scheduling, active same-organization Candidate selection, Manager-owned JD enforcement, scoped idempotent replay/conflict behavior, one-row/one-audit allocation, Manager history, Candidate visibility, and fail-closed tenant reassignment.

## US6 checkpoint — 2026-08-10

- Admin pagination, role-transition, decoder, table, dialog, and composition tests were observed failing before implementation.
- A real PostgreSQL integration test traversed unchanged 1,000-user and 1,000-JD datasets in ten 100-row pages with exact set equality and verified Manager denial.
- Full backend regression: 299 tests passed with exact 100% line and branch coverage; the disposable database was dropped afterward.
- Frontend: 70 component tests passed with exact 100% lines, branches, functions, and statements.
- Contract, Ruff, mypy, strict TypeScript, and ESLint checks passed.

US6 proves application-wide independently paginated minimum user/JD projections, fetched user details, accessible dialog focus/close behavior, all supported role transitions, Candidate profile/provenance retention, old-session revocation, and backend Admin authorization.

## Integrated accessibility/security checkpoint — 2026-08-10

- Eight production-build integrated role-management and accessibility browser journeys passed.
- Axe reported no violations on all three role homes, the open profile disclosure, Manager upload
  error state, and open Admin detail dialog.
- The 320 × 720 Manager error state had no page-level horizontal overflow. Keyboard Escape restored
  focus from both profile disclosure and Admin dialog.
- The named upload/profile/scheduling audit, logging, metrics, error, and temporary-secret controls
  passed the code/evidence review in `security-privacy-review.md`.
- Human NVDA/VoiceOver evidence remains pending in `accessibility-validation.md` and therefore does
  not yet satisfy the manual part of SC-011.

## Migration and recovery checkpoint — 2026-08-10

- On the exact disposable `mockinterview_role_interview_test` database, revision `004` was populated
  with a Manager before upgrading to `005`; the User survived with nullable picture data.
- A feature JD was added, then the isolated `005→004→005` round trip preserved the pre-feature User
  and recreated the feature schema.
- A provenance-linked non-Candidate caused the guarded downgrade to fail with the intended message;
  PostgreSQL transactional DDL left the database at `005`. After resetting the isolated fixture,
  downgrade/re-upgrade succeeded.
- Six domain mapping/participant integration tests passed, including injected participant failure
  and scheduled-interview reassignment rollback. The disposable database was dropped afterward.
- Production recovery remains forward-only: restore a verified backup if required, diagnose on a
  copy, and deploy a new corrective revision rather than using the feature-destructive downgrade.

## Performance checkpoint — 2026-08-10

- The harness first refused a non-dedicated database name. It then created, migrated, and seeded the
  exact `mockinterview_role_interview_performance` database with 1,000 Users and 1,000 JDs.
- Backend read-only baseline, 100 samples at concurrency 10: Candidate p50/p95/max
  16.11/39.47/96.14 ms; Manager 15.92/92.69/99.03 ms; Admin Users
  16.30/23.64/98.21 ms; Admin JDs 16.22/24.18/97.29 ms; zero failures.
- Production-build browser baseline, 100 views across 10 concurrent contexts: 100 successes,
  100 within 2,000 ms, p50 376.55 ms, p95 691.13 ms, max 1,036.77 ms, zero failures.
- The runner copied only sanitized timing reports at mode 0600, then removed the database, API,
  preview process, logs, and raw session/CSRF state. Evidence is under `evidence/`.

SC-004 passes. Participant-dependent timing criteria remain pending and are not inferred from this
automated performance result.

## Full automated blocking gate — 2026-08-10

- Dependency license gate passed for 43 direct dependencies.
- Ruff and strict mypy passed for 40 backend source files.
- Backend: 299 tests passed; exact 100% lines, branches, functions, and statements. Three existing
  non-failing Pydantic alias warnings were emitted by legacy Admin request annotations.
- ESLint and strict TypeScript passed.
- Frontend: 75 component/unit tests passed; exact 100% lines, branches, functions, and statements.
- Playwright: 20 production-build browser journeys passed.
- `bash scripts/quality-gate.sh` exited successfully against the migrated disposable
  `mockinterview_role_interview_test` database, which was dropped afterward.

T100 passes against `.coverage-thresholds.json`, the required coverage source of truth.

## Requirements traceability and release status

| Requirement | Evidence | Status |
|---|---|---|
| FR-001–FR-004 | Google-only callback/contract, role routing, session lifecycle, global logout API/browser tests | Pass |
| FR-005–FR-008 | Verified picture claim, `/auth/me`, profile image/menu/page, logout keyboard flow tests | Pass |
| FR-009–FR-011 | Self-scoped Candidate endpoint and two-Candidate isolation/API/browser tests | Pass |
| FR-012–FR-018 | JD schema, owned list, manual/upload APIs, bounded parser and rollback tests | Pass |
| FR-019–FR-024 | Interview schema, Manager scheduling/list, Candidate projection, idempotency and six availability-race tests | Pass |
| FR-025–FR-029 | Global Admin users/JDs, detail/role change, independent 1,000-record pagination test | Pass |
| FR-030–FR-034 | Backend role dependencies, owner/tenant query predicates, direct-denial contract/browser matrix | Pass |
| SC-001 | All three roles reach their correct home in callback and browser verification | Pass |
| SC-002 | Cross-role, cross-Candidate, cross-Manager, tenant, and ownership denials disclose no protected payload | Pass |
| SC-003 | Requires at least 19/20 unassisted human first attempts | Pending T097 |
| SC-004 | 100/100 real-API production-build views within two seconds under 10-context load | Pass |
| SC-005 | Both Manager flows work automatically; separate five-person timing samples are mandatory | Pending T097 |
| SC-006 | Scheduling flow works automatically; five human timing samples are mandatory | Pending T097 |
| SC-007 | Idempotent scheduling produces one Manager/Candidate row and no other Candidate visibility | Pass |
| SC-008 | 1,000-user Admin flow works automatically; five human timing samples are mandatory | Pending T097 |
| SC-009 | Exact set equality across unchanged 1,000-user and 1,000-JD pagination | Pass |
| SC-010 | Requires at least 18/20 unassisted human primary-task completions | Pending T097 |
| SC-011 | Keyboard, responsive, focus and axe automation pass; human screen-reader evidence is mandatory | Pending T096 |

All observable functional requirements and automated gates pass. Final release sign-off and T101
remain blocked solely by the explicitly human T096/T097 evidence; no participant or screen-reader
result has been fabricated.
