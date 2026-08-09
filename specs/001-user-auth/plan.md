# Implementation Plan: User Authentication and Role Access

**Branch**: `001-user-auth` | **Date**: 2026-08-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-user-auth/spec.md`

## Summary

Build the v1 authentication and authorization foundation as modules in a Python 3.12 FastAPI API
and strict React TypeScript web application. Google OpenID Connect authenticates only Admin-
pre-provisioned users. The backend binds a verified Google subject to one application user,
creates an opaque PostgreSQL-backed session, enforces organization/role/resource policies, and
records secret-safe audit events. The frontend consumes only minimal current-user context through
an HTTP-only cookie session and provides accessible role-specific routing and recovery guidance.

The design includes global session invalidation on logout, role change, or account disablement;
one-to-one Candidate User/Profile association; scoped Manager readiness-report authorization; a
Google-only surface; deterministic test adapters; 100% configured coverage gates; and a
non-blocking performance baseline with no fixed v1 throughput or latency target.

## Technical Context

**Language/Version**: Python 3.12; TypeScript in strict mode

**Primary Dependencies**: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL async driver, Authlib,
Cryptography, Pydantic Settings; React, React Router, Vitest, React Testing Library, Playwright

**Storage**: PostgreSQL for organizations, users, external identities, Candidate-profile links,
application sessions, OAuth transactions, and audit events

**Testing**: pytest with pytest-cov and deterministic OIDC fakes; Vitest with 100% line, branch,
function, and statement coverage; Playwright for integrated browser and accessibility journeys

**Target Platform**: Linux containers; current repository is greenfield and has no application
runtime yet

**Project Type**: Monorepo web application with a modular FastAPI backend and React frontend

**Performance Goals**: Record representative throughput, p50 latency, and p95 latency before
release; results are a non-blocking baseline and do not impose a numeric v1 gate

**Constraints**: Google-only authentication; pre-provisioned users; deny-by-default server-side
authorization; 8-hour absolute and 2-hour idle session limits; all-session revocation on logout,
role change, or disablement; WCAG 2.2 AA; secrets never exposed or logged

**Scale/Scope**: Internal v1, tenancy-ready single-organization operation, unlimited concurrent
sessions per enabled user; no public registration, password authentication, MFA, or downstream
JD/interview/report business implementation

## Constitution Check

*GATE: Evaluated before research and re-checked after Phase 1 design.*

| Principle | Pre-design | Design evidence |
|---|---|---|
| I. Modular Architecture | PASS | Auth, OIDC adapter, session service, audit service, and reusable authorization policy have explicit boundaries in [research.md](./research.md). |
| II. Strict Types and Validated Boundaries | PASS | Runtime validation covers environment configuration, OAuth claims, API payloads, and frontend `unknown` responses; Python and TypeScript remain strictly typed. |
| III. Security, Privacy, Least Privilege | PASS | Server-verified OIDC, opaque hashed sessions, state/nonce/PKCE, global revocation, deny-by-default policy, safe errors, and a named security/privacy review are required. |
| IV. Versioned Data and API Contracts | PASS | The planning workflow initialized the previously empty Git metadata with repository-owner approval; [data-model.md](./data-model.md) defines forward-migrated tenancy constraints and the contracts define interfaces. Setup re-verifies the worktree before migrations. |
| V. Layered Testing | PASS | Unit, contract, PostgreSQL integration, deterministic adapter, browser E2E, accessibility, collision, isolation, and lifecycle scenarios are listed in [quickstart.md](./quickstart.md). |
| VI. Acceptance-Criteria Delivery | PASS | Clarified FR-001–FR-016 and SC-001–SC-009 map to design artifacts; no implementation unknown remains. |
| VII. Dependency Discipline | PASS | [research.md](./research.md) justifies each new dependency and rejects Redis/JWT/additional frontend state or validation libraries for v1. |
| VIII. Observable Failures | PASS | Correlation IDs, structured events, safe reason codes, audit records, session metrics, and non-blocking baseline evidence are defined. |
| IX. Accessible UX | PASS | Contracts and [quickstart.md](./quickstart.md) require keyboard, focus, live-region, contrast, automated axe, and manual screen-reader verification. |

### Post-Design Gate

PASS. The Phase 1 artifacts preserve organization/ownership fields, document API and policy
contracts, specify migration recovery, define deterministic layered tests, and contain no
constitution exception. The first regenerated task re-verifies the valid Git worktree before any
migration is created. Implementation must regenerate
`tasks.md` from these artifacts and run the
project's coverage, security/privacy, accessibility, and plan/task consistency gates before it can
be considered complete.

## Phase 0: Research Decisions

Research is consolidated in [research.md](./research.md). Key decisions are:

1. Use Authorization Code + OpenID Connect through a backend-only Authlib adapter.
2. Pre-provision users by normalized email, then atomically bind the first verified Google login
   to an unbound active user; subsequent logins resolve only `(issuer, subject)`.
3. Use opaque, high-entropy session secrets with only a SHA-256 digest stored in PostgreSQL.
4. Store sessions in PostgreSQL so role/status mutation, global revocation, and audit insertion can
   share a transaction without adding Redis.
5. Use an HTTP-only, `SameSite=Lax`, host-only session cookie plus a separate readable CSRF cookie;
   validate the matching CSRF header/digest and exact Origin on mutations.
6. Model authorization as typed capability and resource scope decisions consumed by FastAPI
   dependencies; do not create fake production JD/report endpoints.
7. Keep frontend state local to a small auth provider with exhaustive role/error mappings and
   runtime response decoders.
8. Encrypt transient PKCE verifiers with a rotated application key supplied only through validated
   environment configuration.
9. Split coverage enforcement by backend/frontend while preserving the repository's 100% source-
   of-truth thresholds and updating existing CI/pre-push consumers.

## Phase 1: Design

### Persistence and Lifecycle

[data-model.md](./data-model.md) defines Organization, User, ExternalLoginIdentity,
CandidateProfile, AuthenticationSession, OAuthTransaction, and AuditEvent. Database constraints
enforce uniqueness and tenancy where possible; services enforce cross-entity invariants in one
transaction, including Candidate-profile readiness and all-session revocation during role/status
changes.

### HTTP and Authorization Interfaces

[auth.openapi.yaml](./contracts/auth.openapi.yaml) defines:

- `GET /api/v1/auth/google/login`
- `GET /api/v1/auth/google/callback`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- `POST /api/v1/admin/users`
- `PATCH /api/v1/admin/users/{user_id}/role`
- `PATCH /api/v1/admin/users/{user_id}/status`

[access-policy.md](./contracts/access-policy.md) defines Candidate ownership, Manager managed-
interview scope, Admin capabilities, organization isolation, and reusable dependency behavior.
Downstream JD, allocation, interview, and report data behavior remains outside this feature.

### Validation

[quickstart.md](./quickstart.md) defines configuration, migration, role login, first binding,
collision, permission matrix, global logout, role/status revocation, expiry, safe recovery,
Google-only surface, audit, accessibility, coverage, security/privacy, and performance-baseline
validation scenarios.

### Pre-Implementation Environment Gate

Before any scaffold or migration task, run `git rev-parse --git-dir`. The previously empty Git
metadata was initialized during planning with repository-owner approval, so this check now
succeeds. If it later fails, implementation stops before creating migrations. Migration changes
must be included in normal verified commits and never bypass repository hooks.

## Project Structure

### Documentation (this feature)

```text
specs/001-user-auth/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── auth.openapi.yaml
│   └── access-policy.md
└── tasks.md                 # regenerated by $speckit-tasks after plan approval
```

### Planned Source Code (created during implementation)

```text
apps/
├── api/
│   ├── app/
│   │   ├── auth/           # OIDC adapter, models, services, policies, routes, audit
│   │   ├── admin/          # pre-provisioning and role/status mutation routes
│   │   └── core/           # configuration, database, observability, middleware
│   ├── migrations/
│   ├── scripts/
│   └── tests/
│       ├── unit/
│       ├── contract/
│       └── integration/
└── web/
    ├── src/
    │   ├── auth/
    │   ├── navigation/
    │   └── test/
    └── e2e/

specs/001-user-auth/performance/   # non-blocking baseline result schema and evidence

scripts/
└── quality-gate.sh                # backend + frontend blocking quality/coverage runner

.coverage-thresholds.json          # per-suite commands and 100% source of truth
.github/workflows/ci.yml           # Python, PostgreSQL, Node, and quality-gate integration
.husky/pre-push                    # invokes the same quality gate without eval
```

**Structure Decision**: Use `apps/api/app` and `apps/web/src` consistently. Authentication remains
a module in the application API, not a new service. PostgreSQL migrations live with the API under
`apps/api/migrations`. The current repository contains documentation and orchestration files only;
all planned application paths must be created by ordered setup tasks before files beneath them are
implemented.

## Complexity Tracking

No constitution violation or complexity exception is required. PostgreSQL-backed sessions reuse
the system of record and avoid a second persistence service; handwritten frontend runtime decoders
avoid adding a validation library solely for the initial auth contract.
