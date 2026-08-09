<!--
Sync Impact Report
- Version change: template (unratified) -> 1.0.0
- Added principles:
  - I. Modular Architecture and Pattern Reuse
  - II. Strict Types and Validated Boundaries
  - III. Security, Privacy, and Least Privilege
  - IV. Versioned Data and API Contracts
  - V. Layered Testing (NON-NEGOTIABLE)
  - VI. Acceptance-Criteria-Driven Delivery (NON-NEGOTIABLE)
  - VII. Simplicity and Dependency Discipline
  - VIII. Observable and Actionable Failures
  - IX. Accessible User Experience
- Added sections:
  - Product and Technical Constraints
  - Development Workflow and Quality Gates
- Removed sections: none; template placeholders were replaced.
- Follow-up TODOs: none.
-->

# MockInterview Constitution

## Core Principles

### I. Modular Architecture and Pattern Reuse
The system MUST be organized into cohesive modules with explicit responsibilities and stable
interfaces. Real-time transport, interviewer orchestration, proctoring, scoring, reporting,
identity, and external vendors MUST remain independently replaceable where their responsibilities
differ. New work MUST extend an existing module, interface, or established pattern when one fits;
creating a new architectural pattern requires documented evidence that existing patterns cannot
meet the acceptance criteria. Modules MUST be independently testable and dependencies MUST flow
through documented interfaces rather than hidden global state.

Rationale: MockInterview is a multi-service, real-time product whose vendors and operational
requirements will evolve. Clear boundaries contain change and prevent parallel implementations of
the same responsibility.

### II. Strict Types and Validated Boundaries
TypeScript MUST use strict compiler settings and MUST NOT introduce `any` without a documented,
reviewed exception at an external compatibility boundary. Python production code MUST use type
annotations and pass the configured static type checker. Every untrusted input MUST be validated
before reaching business logic, including HTTP and WebSocket payloads, OAuth claims, uploaded
files, LLM output, webhook events, environment configuration, and persisted JSON. Validation
failures MUST return safe, documented errors and MUST NOT be silently coerced.

Rationale: Static types prevent internal ambiguity; runtime validation is still required because
network, user, model, and vendor inputs cannot be trusted.

### III. Security, Privacy, and Least Privilege
Authentication MUST use the approved identity provider and server-verified credentials.
Authorization MUST be enforced server-side for every protected operation and data access using a
deny-by-default role and ownership policy. Candidate, Manager, Admin, Mentor, and service access
MUST be limited to the minimum data and actions required; UI visibility alone is never an access
control. Secrets MUST enter the system only through environment variables or an approved secret
configuration provider and MUST never appear in source, fixtures, logs, client bundles, or version
control.

Sensitive flows—including login, role changes, recording consent, uploads, proctoring, recordings,
transcripts, scoring, mentor sign-off, exports, retention, and deletion—MUST receive a documented
security and privacy review before release. Recordings and sensitive candidate data MUST be
encrypted in transit and at rest. Security-relevant events MUST be auditable without exposing
secret or unnecessarily sensitive content.

Rationale: The product processes identity, biometric-like signals, recordings, evaluations, and
employment-related recommendations. A failure can harm candidates and the organization.

### IV. Versioned Data and API Contracts
Every relational schema change MUST be represented by a forward migration under version control;
production databases MUST NOT depend on manual or unrecorded schema edits. Migrations MUST define
rollback or forward-recovery handling, preserve required data, and be tested against a realistic
schema state. Tenancy and ownership fields required by the architecture MUST be preserved across
all applicable tables.

HTTP, WebSocket, event, and service APIs MUST have documented contracts, including schemas,
authentication, authorization, error responses, and compatibility expectations. FastAPI OpenAPI
output SHOULD be the executable source for HTTP contract documentation. Breaking contract changes
MUST be explicitly versioned and include a consumer migration plan.

Rationale: Auditable migrations and explicit contracts allow independently deployed services and
clients to evolve without hidden coupling or data loss.

### V. Layered Testing (NON-NEGOTIABLE)
Business rules MUST have deterministic unit tests, including interview-plan composition, probe
state transitions, rubric calculations, integrity thresholds, access policy decisions, retention
rules, and report verdicts. API, database, queue, object-storage, and external-adapter boundaries
MUST have integration tests that exercise serialization, persistence, transactions, failures, and
authorization. Critical user journeys MUST have end-to-end tests, at minimum authentication and
role routing, interview allocation, candidate pre-flight and session recovery, mentor review and
sign-off, and authorized report access.

Tests MUST cover success, denial, invalid-input, and material failure paths. External AI and media
providers MUST be exercised through deterministic fakes in routine tests, with separately marked
contract or staging tests where real-provider behavior must be verified. Required tests and the
project coverage threshold MUST pass before work is considered complete.

Rationale: Unit tests protect decisions, integration tests protect boundaries, and end-to-end tests
protect the user outcomes that justify the product.

### VI. Acceptance-Criteria-Driven Delivery (NON-NEGOTIABLE)
No implementation may begin until the work has explicit, testable acceptance criteria describing
observable behavior, relevant error and authorization cases, and measurable non-functional limits
where applicable. Each implementation change MUST trace to at least one acceptance criterion, and
each criterion MUST be verified by an automated test or an explicitly documented manual check when
automation is not feasible. Ambiguous or conflicting criteria MUST be clarified before coding.

Rationale: Acceptance criteria keep implementation aligned with product outcomes and prevent
unverifiable scope from entering the system.

### VII. Simplicity and Dependency Discipline
The team MUST prefer platform capabilities, standard libraries, and existing approved project
dependencies over adding packages. A new dependency requires a documented need, comparison with
existing options, maintenance and security assessment, license compatibility, and justification
of its runtime or build impact. Duplicate libraries for the same concern are prohibited unless a
reviewed migration plan requires temporary overlap. Speculative abstractions, unused extension
points, and premature distribution MUST NOT be added.

Rationale: Every dependency and abstraction expands the security, operational, upgrade, and
cognitive burden of a long-lived multi-service system.

### VIII. Observable and Actionable Failures
Services MUST emit structured logs with consistent severity, event names, timestamps, request or
session correlation identifiers, and safe diagnostic context. Errors MUST be visible to the
responsible operator through appropriate logs, metrics, traces, or alerts; they MUST NOT be
silently swallowed. User-facing errors MUST explain the recovery action without leaking internal,
personal, or secret data. Real-time session health, latency budgets, reconnects, external-provider
failures, scoring retries, and security-relevant events MUST be measurable.

Rationale: Interview sessions are time-bound and auditable. Operators need enough evidence to
recover failures and reconstruct outcomes without exposing candidate data.

### IX. Accessible User Experience
User-facing UI MUST meet WCAG 2.2 AA for applicable flows. Interactive controls MUST support
keyboard operation, visible focus, semantic labels, sufficient contrast, and screen-reader use.
Live interview experiences MUST provide captions, understandable status and error announcements,
and the documented audio-only degradation path. Accessibility requirements MUST be present in
acceptance criteria and tested with automation plus manual keyboard and assistive-technology checks
for critical journeys.

Rationale: Accessibility is part of a fair interview experience and cannot be deferred as visual
polish after functionality is complete.

## Product and Technical Constraints

- The frontend uses React with strict TypeScript; the backend uses Python with FastAPI; PostgreSQL
  is the system of record for relational data.
- Candidate-facing decisions and scores MUST remain explainable and traceable from question to
  response evidence, rubric version, model or prompt version, and human sign-off.
- AI-generated interview and scoring output MUST be treated as untrusted input and MUST remain
  subject to schema validation, grounding rules, and required human review.
- External media, avatar, speech, model, storage, and notification providers MUST be accessed
  through narrow adapters so that business logic does not depend on vendor-specific APIs.
- Personally identifiable information, recordings, transcripts, proctoring evidence, and scores
  MUST follow documented retention, deletion, consent, and role-based access policies.
- Performance requirements from approved feature specifications, especially live-media latency and
  reconnect targets, MUST be measured in representative tests and observable in production.

## Development Workflow and Quality Gates

1. Define or confirm acceptance criteria and affected security, privacy, accessibility, API, and
   data requirements before implementation.
2. Inspect the existing architecture and record which module or pattern will be reused. Any new
   pattern or dependency MUST include the justification required by this constitution.
3. Write or update the necessary unit, integration, contract, and end-to-end tests. Tests SHOULD
   fail for the intended reason before implementation when test-first development is practical.
4. Implement the smallest change that satisfies the criteria while preserving module boundaries
   and strict typing.
5. Update API documentation, migrations, observability, operational guidance, and security or
   privacy records in the same change when affected.
6. Reviewers MUST verify acceptance-criteria traceability, authorization, validation, migration
   safety, API compatibility, test evidence, structured logging, dependency justification, and
   accessibility before approval.
7. Sensitive flows MUST pass a named security and privacy review. Critical user journeys MUST pass
   end-to-end verification before release.

## Governance

This constitution is the highest-priority engineering policy for MockInterview. Feature
specifications, plans, tasks, pull requests, and reviews MUST demonstrate compliance. When a local
practice conflicts with this constitution, the constitution governs unless it is formally amended.

Amendments require a written proposal that states the motivation, affected principles, migration
or remediation impact, and approval from the designated engineering owner. Constitution versions
follow semantic versioning: MAJOR for incompatible governance changes or principle removals, MINOR
for new principles or materially expanded requirements, and PATCH for non-semantic clarification.
The amendment date and Sync Impact Report MUST be updated with every change.

Every feature plan and pull request MUST include a constitution compliance check. Exceptions MUST
name the violated rule, explain why compliance is currently impossible, define compensating
controls, identify an owner, and include an expiry or remediation date. Permanent exceptions
require a constitution amendment. The engineering owner MUST review the constitution at least
quarterly and after any material security, privacy, accessibility, or production incident.

**Version**: 1.0.0 | **Ratified**: 2026-08-09 | **Last Amended**: 2026-08-09
