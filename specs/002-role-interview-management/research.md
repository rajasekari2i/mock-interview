# Phase 0 Research: Role-Based Interview Management

## Existing architecture and reuse boundary

**Decision**: Extend the current auth/Admin modules and add cohesive `jds` and `interviews` API
modules. Keep one request-owned `AsyncSession` transaction, stable AuthError envelope, exact-origin
CSRF, append-only audit, correlation middleware, capability policy, strict frontend decoder, and
100% quality-gate patterns.

**Rationale**: These boundaries already protect Google login, role changes, sessions, tenant
ownership, and Admin mutations. Reuse avoids a second authorization or transaction model.

**Alternatives considered**: A new service/repository framework was rejected as duplicate
architecture. Database row-level security remains a possible defense-in-depth layer but would add
an operational model well beyond this feature.

## Authenticated profile and Google picture

**Decision**: Add nullable `users.profile_picture_url`; decode optional `picture` only after the ID
token passes signature, issuer, audience, expiry, nonce, and email verification. Accept a bounded
absolute HTTPS URL on an approved Google-hosted image domain; otherwise store null. Refresh the
name/picture on successful login and extend `/auth/me` with `email` and `profilePictureUrl`.

**Rationale**: `/auth/me` already supplies the signed-in identity and session. One response can
power the header and profile page without provider tokens or a second lookup. Null supports an
accessible placeholder.

**Alternatives considered**: A profile table adds no value for three read-only identity fields.
Calling Google UserInfo per page adds tokens, latency, and availability coupling. Server-side image
proxying introduces SSRF and caching/storage lifecycle concerns.

## JD upload ingestion and dependency discipline

**Decision**: Accept multipart PDF, DOCX, and UTF-8 TXT up to 5 MiB. Stream to a bounded in-memory
buffer; validate extension, declared type, signature/container, encryption/macro state, archive
entry/count/ratio limits, and extracted-text limits. Persist only normalized canonical text (at
most 500,000 characters), document format, title, source kind, owner, organization, and timestamps;
discard the original and filename. Use a narrow adapter backed by pinned `python-multipart`,
`pypdf`, and `python-docx`.

**Rationale**: FastAPI's official file-upload boundary uses multipart and `UploadFile`, while OWASP
recommends extension allowlists, non-header type validation, signatures, size/decompression limits,
authorization, CSRF, and storage outside public paths. Canonical text satisfies later use without
retaining or serving potentially malicious originals. The selected packages support Python 3.12
and have compatible Apache-2.0, BSD-3-Clause, and MIT licenses. Sources:
[FastAPI request files](https://fastapi.tiangolo.com/tutorial/request-files/),
[OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html),
[python-multipart](https://pypi.org/project/python-multipart/),
[pypdf](https://pypi.org/project/pypdf/), and
[python-docx](https://pypi.org/project/python-docx/).

**Alternatives considered**: Raw files in PostgreSQL duplicate sensitive content and enlarge
backups. Object storage/quarantine adds unconfigured infrastructure and a multi-step lifecycle.
Handwritten PDF/DOCX parsers are an unsafe dependency-avoidance exercise. Browser-side parsing is
untrusted and inconsistent.

## JD persistence and ownership

**Decision**: Use one `job_descriptions` record containing tenant, creator, title, canonical text,
source kind, optional upload format, and timestamps. A composite creator/tenant foreign key and
owner-first indexes enforce and accelerate Manager-owned and Admin application-wide projections.
Managers query by authenticated owner; Admins receive a minimum list projection without content.

**Rationale**: The record contains everything required to identify and use a JD for scheduling
without adding file lifecycle state. Ownership predicates prevent fetch-then-filter disclosure.

**Alternatives considered**: A separate document table is unnecessary when originals are not
retained. Storing only a path requires a storage system that does not exist.

## Scheduling model, time, and idempotency

**Decision**: A `scheduled_interviews` row is the allocation. It associates tenant, Candidate User,
Manager User, JD, aware UTC `scheduled_at`, initial `SCHEDULED` status, a scoped idempotency-key
digest, request fingerprint, and timestamps. `POST /manager/interviews` requires an opaque UUID
`Idempotency-Key`. Identical retries return the original; same key with changed input returns 409.
Different keys intentionally create separate interviews.

**Rationale**: One row makes Manager and Candidate views atomic. An aware RFC 3339 instant avoids
browser/server timezone ambiguity. Idempotency prevents network retries and double-submits without
prohibiting legitimate repeated Candidate/JD/time combinations.

**Alternatives considered**: A separate allocation table can diverge. A unique
Candidate/JD/timestamp constraint blocks legitimate distinct interviews. UI button disabling does
not stop retries or concurrency. Separate date/time fields require an organization timezone that
is not in scope.

## Transaction and concurrency boundary

**Decision**: Manual JD creation, extracted upload persistence, and scheduling each complete inside
the existing request transaction. Scheduling locks and revalidates the active same-organization
Candidate and Manager-owned JD, checks `scheduled_at > now`, resolves idempotency, inserts the row,
and audits before the single request commit. Parser work is bounded and runs outside the event loop,
but no database row is created until extraction succeeds.

**Rationale**: This matches the current service contract (no nested commit/rollback) and ensures no
partial JD, interview, allocation, or audit state.

**Alternatives considered**: A background parse workflow needs pending/failed product states that
were not requested. SERIALIZABLE isolation for every route is unnecessary; row locks plus unique
idempotency constraints address the actual races.

Two-session PostgreSQL tests use deterministic barriers to race scheduling against Candidate
disable/role change, Manager disable/role change, and a fixture-driven JD owner/tenant change. Both
lock orders are required: mutation-first must make scheduling wait and then reject without an
interview or audit, while scheduling-first may commit one complete interview and audit before the
mutation proceeds. Partial rows, orphan audits, and stale-owner successes are forbidden.

## Pagination

**Decision**: Use page-number pagination with `page >= 1`, default `pageSize=25`, maximum 100,
`totalItems`, and `totalPages`. Apply deterministic `created_at DESC, id DESC` ordering for users/JDs
and `scheduled_at ASC, id ASC` for interview lists. Use minimum projection queries and composite
owner/tenant/order indexes.

**Rationale**: This matches the requested server pagination and proves no skips/duplicates for the
specified unchanged result set at 1,000 records. Independent user/JD page query parameters preserve
Admin browser history.

**Alternatives considered**: Cursor pagination is stronger during concurrent mutation but adds
contract and UI complexity not required by the acceptance criteria. Unbounded lists fail both
privacy and performance goals.

Each response is independently authorized and bounded even when records change between page
requests. Tests mutate the ordered dataset between requests and assert valid page metadata,
page-size limits, minimum projections, and absence of unauthorized rows; they intentionally do not
promise unchanged-set exact traversal while the dataset is changing.

## Authorization and Admin scope

**Decision**: Add explicit Candidate, Manager, and Admin feature capabilities. Candidate and
Manager endpoints derive user/owner IDs from the authenticated session, never request parameters.
Manager candidate selection is limited to active Candidates in the same organization and exposes
only ID, name, and email. Non-owned/cross-tenant details return a generic 404; wrong-role requests
return 403. Admin user/JD lists are application-wide as explicitly specified; v1 currently operates
as one active tenant, while returned records retain organization identity internally.

**Rationale**: Query-scoped ownership is deny-by-default and cannot be bypassed by a direct request.
The explicit application-wide Admin requirement governs over inventing a narrower permission.

**Alternatives considered**: UI-only guards violate FR-030. Fetch-then-filter can leak existence.
Organization-only Admin scope was rejected because the feature says all application users/JDs.

## Role transitions and preserved history

**Decision**: Revision `005` removes the constraint that provenance-linked users must forever have
the Candidate role. Admin role changes retain immutable registration provenance and any
CandidateProfile as dormant history; entering Candidate creates the profile if absent. Every real
role change locks the User, increments auth generation, revokes all sessions, audits, and takes
effect only after fresh login. Interview rows reference stable User IDs, not CandidateProfile.

**Rationale**: The current Candidate-to-Manager/Admin rejection conflicts with FR-027. Preserving
profiles, provenance, and allocations avoids destructive history repair and supports later return
to Candidate.

**Alternatives considered**: Keeping the rejection violates the feature. Deleting profiles or
clearing provenance destroys security/audit history. Leaving sessions alive retains stale access.

## Tenant reassignment with multi-owner interviews

**Decision**: JobDescriptions use the existing composite ownership `ON UPDATE CASCADE` convention.
Scheduled interviews use immediate same-tenant foreign keys and register a deterministic
`scheduled_interviews` migration participant. The participant locks and rejects domain
reassignment when any affected provenance-linked User participates as Candidate or scheduling
Manager in an interview. The database foreign keys remain a second fail-closed defense.

**Rationale**: An interview is jointly related to a Candidate, Manager, and Manager-owned JD.
Moving only one party would create cross-tenant disclosure; the existing migration contract allows
an unmigratable business invariant to abort the entire mapping reassignment.

**Alternatives considered**: Moving the interview alone strands its Manager/JD. Copying or
snapshotting parties invents a migration policy. Deferrable multi-owner cascades still cannot make
a final cross-tenant state valid. Silent omission violates the existing migration completeness
contract.

## API, CSRF, safe errors, audit, and observability

**Decision**: Define the feature in `contracts/role-interview.openapi.yaml`. All writes use the
existing session cookie, exact Origin, CSRF header/cookie match, stable error envelope, and
correlation ID. The application CORS allow-header list adds `Idempotency-Key`, and credentialed
approved/unapproved-origin preflight behavior is tested. Upload errors distinguish invalid request
(400), too large (413), and unsupported
or unreadable content (415); idempotency mismatch uses 409. Successful sensitive mutations audit in
their transaction; denial audits use an independent safe transaction. Extend metrics/structured
events to JD, scheduling, pagination, replay/conflict, and bounded parser rejection categories.

**Rationale**: The existing web-session threat model and frontend recovery contract already work.
Safe categories are actionable without recording confidential JDs or user identity.

**Alternatives considered**: SameSite alone is insufficient CSRF evidence. Idempotency is not CSRF
protection. Default framework validation envelopes would create a second client error contract.
Logging request bodies, filenames, titles, emails, or keys is prohibited.

The existing `specs/001-user-auth/contracts/auth.openapi.yaml` remains executable for authentication
and is updated in the same change. Contract tests require its `/auth/me` fields to match this
feature contract, preventing two authoritative schemas from drifting. Its Admin role-change text
and executable regression are also updated to permit provenance-preserving transitions away from
Candidate; the obsolete CandidateProfile-conflict rule is removed from that contract.

## Frontend shell, routing, and accessibility

**Decision**: Activate the installed React Router with role roots and common `/profile` inside an
AuthenticatedShell. Use a native disclosure (button, link, logout button) for profile actions and
native `<dialog>` for Admin user details. Candidate, Manager, and Admin modules own strict
types/decoders and async states. Tables remain semantic; controls restore focus, announce status,
support keyboard operation, show non-color status text, and retain the existing focused-heading
pattern.

**Rationale**: Declarative routes give stable deep links and backend-aligned role boundaries.
Native elements minimize custom focus/menu/dialog failure modes and support WCAG 2.2 AA.

**Alternatives considered**: Pathname switches and monolithic role pages duplicate routing logic.
A partial ARIA menu requires unnecessary roving focus. A custom modal requires a bespoke focus trap,
inert background, Escape, and restoration implementation.

## Testing and release evidence

**Decision**: Follow red-green TDD across pure policies/parsers/idempotency, authored/generated
contract checks, populated migration tests, real PostgreSQL integration/concurrency, React
components/decoders, Playwright user journeys, axe/keyboard checks, manual NVDA or VoiceOver, and a
repeatable 1,000-record performance baseline. The root quality gate remains blocking at exact 100%
for backend and frontend metrics.

**Rationale**: The constitution and `.coverage-thresholds.json` require all layers; uploads,
authorization, migration, role revocation, and scheduling races cannot be proven by happy-path unit
tests alone.

**Alternatives considered**: SQLite cannot prove PostgreSQL locks/constraints. Mock-only browser
tests cannot prove integrated navigation/focus. Automated accessibility alone cannot establish
screen-reader usability.

The existing authentication contract and the feature contract use the production
`__Host-mi_session` cookie name, and executable contract tests compare their security schemes as
well as their shared `/auth/me` schema. Clean-environment setup installs locked dependencies and
then installs `apps/api` editable with `--no-deps`, so standalone scripts can import `app` without
allowing dependency resolution to drift from the lock file.

Rendered-page performance uses a separate guarded harness, not the mock-based browser gate. The
harness owns a dedicated database, migrations, deterministic seed/session artifacts in a temporary
permission-restricted directory, real API lifecycle, optimized frontend build/preview lifecycle,
preview proxy, health waits, Playwright performance config, and cleanup trap. This makes the SC-004
measurement reproducible without assuming a manually running application.
The performance spec lives under `apps/web/performance`, while the normal Playwright configuration
discovers only `apps/web/e2e`; neither lifecycle can collect the other's tests.

Alembic currently reads only the URL in `alembic.ini`, so `env.py` will gain a narrowly named
`MOCKINTERVIEW_MIGRATION_DATABASE_URL` override with tested precedence over that fallback. The
performance runner validates the exact dedicated database name first and then exports both this
migration URL and the API runtime `DATABASE_URL` to the identical target, preventing migrations,
seeding, and the real API from accidentally using different databases.
Clean setup and the performance runner both invoke the pinned Playwright CLI's idempotent Chromium
and Linux-dependency installation, so browser validation does not depend on an undeclared
user-level browser cache or host libraries. The standalone runner exports all required `Settings`
fields explicitly with `APP_ENV=test`, generated test-only provider values and Fernet key, fixed
policy durations/paths, dedicated callback/origins, a non-Secure performance cookie, and fake OIDC;
it does not depend on `.env.local` or real credentials, and cleanup removes temporary secrets and
session artifacts.
