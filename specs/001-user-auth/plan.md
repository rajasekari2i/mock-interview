# Implementation Plan: User Authentication and Role Access

**Branch**: `001-user-auth` | **Date**: 2026-08-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-user-auth/spec.md`

## Summary

Extend the implemented v1 authentication and authorization foundation with controlled first-login
Candidate registration. Existing independently pre-provisioned users retain first-email binding
without requiring a mapping. Only when no User matches must the verified Google email domain match
one active PostgreSQL-backed organization mapping exactly; the callback then atomically creates the
Candidate User, profile, Google identity, session, provenance link, and audit events. Admin-only
APIs create, list, remove, and reassign mappings with CSRF, authorization, validation, and audit.

Mapping removal disables exactly its self-registered Candidates and revokes their sessions.
Mapping reassignment transactionally migrates those Candidates and every registered tenant-
migration participant to the new organization, revokes sessions, and rolls back on any failure.
Exact domain matching, provider-signed display-name handling, row locking, cascading tenancy
constraints, migration provenance, and deterministic concurrency/rollback tests preserve the
existing Google-only, deny-by-default, auditable security model.

## Technical Context

**Language/Version**: Python 3.12; TypeScript in strict mode

**Primary Dependencies**: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL async driver, Authlib,
Cryptography, Pydantic Settings; React, React Router, Vitest, React Testing Library, Playwright

**Storage**: PostgreSQL for organizations, active/removed domain mappings, registration provenance,
users, external identities, Candidate-profile links, application sessions, OAuth transactions,
and audit events

**Testing**: pytest with pytest-cov and deterministic OIDC fakes; Vitest with 100% line, branch,
function, and statement coverage; Playwright for integrated browser and accessibility journeys

**Target Platform**: Existing Linux-containerized FastAPI, React/Vite, and PostgreSQL application

**Project Type**: Monorepo web application with a modular FastAPI backend and React frontend

**Performance Goals**: Record representative throughput, p50 latency, and p95 latency before
release; results are a non-blocking baseline and do not impose a numeric v1 gate

**Constraints**: Google-only authentication; exact approved-domain registration; Admin-only mapping
mutation; deny-by-default server-side authorization; transactional tenant migration and rollback;
8-hour absolute and 2-hour idle session limits; all-session revocation on logout, role change,
disablement, mapping removal, or reassignment; WCAG 2.2 AA; secrets never exposed or logged

**Scale/Scope**: Internal multi-organization v1 with explicitly approved Google email domains and
unlimited concurrent sessions per enabled user; Candidate self-registration only, no self-selected
Manager/Admin role, password authentication, MFA, or public organization creation. Current source
has only authentication-owned Candidate data; future organization-owned modules must implement the
documented tenant-migration participant contract before their data can be reassigned.

## Constitution Check

*GATE: Evaluated before research and re-checked after Phase 1 design.*

| Principle | Pre-design | Design evidence |
|---|---|---|
| I. Modular Architecture | PASS | Auth, OIDC adapter, session service, audit service, and reusable authorization policy have explicit boundaries in [research.md](./research.md). |
| II. Strict Types and Validated Boundaries | PASS | Runtime validation covers environment configuration, OAuth claims, API payloads, and frontend `unknown` responses; Python and TypeScript remain strictly typed. |
| III. Security, Privacy, Least Privilege | PASS | Exact approved-domain matching, Admin-only mutation, row locking, atomic rollback, session revocation, server-verified OIDC, safe errors, and a refreshed named security/privacy review are required. |
| IV. Versioned Data and API Contracts | PASS | [data-model.md](./data-model.md) defines forward revision `002`, durable provenance, cascading tenancy constraints, and migration recovery; HTTP and tenant-migration interfaces are explicitly contracted. |
| V. Layered Testing | PASS | Unit, contract, PostgreSQL migration/concurrency/rollback integration, deterministic OIDC, browser E2E, accessibility, collision, isolation, and lifecycle scenarios are listed in [quickstart.md](./quickstart.md). |
| VI. Acceptance-Criteria Delivery | PASS | Clarified FR-001–FR-017 and SC-001–SC-011 map to design artifacts; no implementation unknown remains. |
| VII. Dependency Discipline | PASS | [research.md](./research.md) justifies each new dependency and rejects Redis/JWT/additional frontend state or validation libraries for v1. |
| VIII. Observable Failures | PASS | Correlation IDs, structured events, safe reason codes, audit records, session metrics, and non-blocking baseline evidence are defined. |
| IX. Accessible UX | PASS | Contracts and [quickstart.md](./quickstart.md) require keyboard, focus, live-region, contrast, automated axe, and manual screen-reader verification. |

### Post-Design Gate

PASS. The revised Phase 1 artifacts preserve tenant ownership through cascading composite
constraints and one transaction, document Admin HTTP and tenant-migration participant contracts,
specify revision `002` recovery, and require deterministic race and rollback tests. Historical
AuditEvents remain immutable in their original organization; a new reassignment event records safe
old/new organization identifiers. Implementation must regenerate `tasks.md`, use TDD, and pass the
100% coverage, security/privacy, accessibility, migration, and plan/task consistency gates.

## Phase 0: Research Decisions

Research is consolidated in [research.md](./research.md). Key decisions are:

1. Use Authorization Code + OpenID Connect through a backend-only Authlib adapter.
2. Preserve pre-provisioned first binding, but when no User matches, lock the exact active domain
   mapping and atomically self-register a Candidate with immutable mapping provenance.
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
10. Persist soft-removed domain mappings and a nullable User provenance FK so removal/reassignment
    targets only self-registered Candidates and never independently pre-provisioned users.
11. Serialize registration and mapping mutation with PostgreSQL row locks; change composite tenant
    FKs to `ON UPDATE CASCADE` so authentication-owned child rows follow a locked User move.
12. Revoke sessions with `DOMAIN_MAPPING_REMOVED` or `DOMAIN_MAPPING_REASSIGNED`, increment auth
    generation, migrate authentication-owned tenant rows, and retain historical AuditEvents.
13. Expose Admin-only list/create/reassign/remove mapping APIs and a same-transaction tenant-
    migration participant interface for future Candidate-owned modules.
14. Decode the optional provider-signed Google `name` claim with strict normalization and use a
    validated email local-part fallback.
15. Preserve unbound pre-provisioned email binding without a mapping; treat reassignment to the
    current organization as an idempotent `200` with no migration, revocation, or audit mutation.

## Phase 1: Design

### Persistence and Lifecycle

[data-model.md](./data-model.md) adds OrganizationDomainMapping and User registration provenance,
plus mapping-specific revocation reasons. Revision `002` creates a partial unique active-domain
index and changes authentication child tenancy FKs to `ON UPDATE CASCADE`, so registration,
removal, and reassignment remain atomic. A mapping-row lock is the serialization point. Historical
AuditEvents are immutable and are not rewritten during reassignment.

### HTTP and Authorization Interfaces

[auth.openapi.yaml](./contracts/auth.openapi.yaml) defines:

- `GET /api/v1/auth/google/login`
- `GET /api/v1/auth/google/callback`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- `POST /api/v1/admin/users`
- `PATCH /api/v1/admin/users/{user_id}/role`
- `PATCH /api/v1/admin/users/{user_id}/status`
- `GET /api/v1/admin/organization-domain-mappings`
- `POST /api/v1/admin/organization-domain-mappings`
- `PATCH /api/v1/admin/organization-domain-mappings/{mapping_id}`
- `DELETE /api/v1/admin/organization-domain-mappings/{mapping_id}`

[access-policy.md](./contracts/access-policy.md) defines Candidate ownership, mapping-management
Admin capability, Manager managed-interview scope, Admin capabilities, organization isolation, and
reusable dependency behavior. [tenant-migration.md](./contracts/tenant-migration.md) defines the
same-transaction participant interface that downstream Candidate-owned modules must implement.
Application composition updates CORS to allow `DELETE`, wires mapping routes and migration
participants, and adds one validated frontend application origin used for absolute OAuth
success/error redirects.

### Validation

[quickstart.md](./quickstart.md) adds first-login self-registration, exact/subdomain denial,
Admin mapping CRUD authorization, removal, reassignment, participant rollback, and concurrent
registration/mutation scenarios to the existing auth validation suite.

### Pre-Implementation Environment Gate

Before revision `002`, run `git rev-parse --git-dir`, verify revision `001` is the current deployed
baseline, and snapshot constraint names. Migration changes must be included in normal verified
commits and never bypass repository hooks.

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
│   ├── access-policy.md
│   └── tenant-migration.md
└── tasks.md                 # regenerated by $speckit-tasks after plan approval
```

### Source Code Delta

```text
apps/
├── api/
│   ├── app/
│   │   ├── main.py         # route/participant wiring and CORS DELETE allowlist
│   │   ├── auth/           # OIDC adapter, models, services, policies, routes, audit
│   │   ├── admin/          # user and organization-domain mapping lifecycle
│   │   ├── tenancy/        # migration coordinator and participant protocol
│   │   └── core/           # frontend-origin configuration, database, observability, middleware
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

**Structure Decision**: Extend the existing `apps/api/app/auth` and `apps/api/app/admin` modules.
Add one narrow `tenancy` module because cross-module migration coordination is a distinct required
boundary; do not create a service or dependency. PostgreSQL migration `002` lives beside the
implemented revision `001`. The frontend requires only existing safe error/routing coverage unless
Admin mapping UI is separately specified; this feature contracts Admin APIs only.

## Complexity Tracking

No constitution violation or dependency exception is required. The participant protocol and
cascading tenant constraints add justified complexity because FR-017 explicitly requires atomic
migration of all Candidate-owned tenant data. A single PostgreSQL transaction and existing
AsyncSession are retained; no queue, distributed transaction, Redis, or new package is introduced.
Until another Candidate-owned module exists, no production participant is required: the
coordinator updates locked Users and authentication-owned rows follow `ON UPDATE CASCADE`.
