# Authentication Traceability

This matrix is the release map from the approved requirements to implementation and evidence.

| Requirement | Implementation | Executable/manual evidence |
|---|---|---|
| FR-001 | exact domain lookup in `auth/service.py`, `OrganizationDomainMapping`, Candidate/Profile/Identity atomic creation | identifier, identity-binding, callback, and mapped onboarding tests |
| FR-002 | `google_oidc.py`, `oauth_transactions.py`, auth router | OIDC unit/callback integration and Google-login Playwright tests |
| FR-003 | `ExternalLoginIdentity`, `resolve_or_bind_identity` | identity-binding and callback collision tests |
| FR-004 | strict `Role` enum and discriminated frontend users | policy and role-landing tests |
| FR-005 | Candidate capabilities, owner scope, Candidate navigation | policy/Manager-scope tests and role-access journey |
| FR-006 | Admin capabilities and Admin router dependency | policy, mutation, and protected-route tests |
| FR-007 | Manager allocation/managed-readiness scopes | Manager-scope unit tests and role-aware navigation journey |
| FR-008 | authenticated request and deny-by-default policy dependencies | authorization-dependency integration tests |
| FR-009 | one-time callback transaction and safe error taxonomy | OIDC, callback replay, error, and login E2E tests |
| FR-010 | PostgreSQL sessions, generation, revoke-all, 8h/2h deadlines | session, logout, revocation, expiry, and two-context tests |
| FR-011 | only Google routes and views | `test_google_only_auth.py`, `GoogleOnlyAuth.test.tsx` |
| FR-012 | stable `ErrorCode`/`RecoveryAction`, protected UI states | error contract, AuthFlow, ProtectedRoutes, session recovery tests |
| FR-013 | per-request session validation and no-store/history headers | logout/session integration tests and lifecycle E2E |
| FR-014 | unique same-org CandidateProfile plus transactional service invariant | schema, provisioning, binding, and role-transition tests |
| FR-015 | append-only application audit API, correlation and safe metadata allowlist | audit-producing integration tests, observability and metrics tests |
| FR-016 | semantic/live views, focused headings, keyboard-native controls | auth accessibility Playwright and manual checklist |
| FR-017 | revision `002`, Admin mapping routes/service, provenance FK, advisory locks, cascading tenant FKs, participant coordinator | mapping contract/lifecycle/collision/rollback and independent-session concurrency tests |

| Criterion | Evidence |
|---|---|
| SC-001 | callback and three-role Google-login journeys |
| SC-002 | exhaustive policy matrix and denial integration tests |
| SC-003 | owner/org policy tests and Candidate-only navigation |
| SC-004 | callback/error/session suites |
| SC-005 | global logout, revocation, expiry, two-context lifecycle suites |
| SC-006 | backend and frontend Google-only absence tests |
| SC-007 | `security-privacy-review.md` |
| SC-008 | automated axe suite and `accessibility-validation.md` |
| SC-009 | fixed baseline script, schema, and recorded baseline JSON |
| SC-010 | mapped/unmapped callback and identity-binding tests with exact row-count assertions |
| SC-011 | Admin authorization, soft-removal, reassignment, participant failure, target collision, and race tests |

Acceptance scenarios are exercised by the four story-specific unit/integration/component/E2E
groups in `tasks.md`. Explicit non-goals remain absent: interview execution, profile editing,
scoring/report implementation, JD processing, scheduling, password authentication, and roles
outside Candidate/Admin/Manager. Test-only protected fixtures prove policy integration without
creating placeholder production domains.
