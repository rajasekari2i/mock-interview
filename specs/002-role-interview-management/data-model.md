# Data Model: Role-Based Interview Management

## Design principles

- PostgreSQL remains the relational system of record and every new entity carries explicit tenant
  and ownership information.
- Stable User IDs, not role-specific profile IDs, anchor JD ownership and interview participation.
- Database constraints provide a second defense beneath service authorization.
- List queries project only required columns; canonical JD content is never loaded for home-screen
  or Admin table responses.
- All timestamps are timezone-aware and stored as absolute instants.
- Revision `005` is forward-only for production recovery; downgrade is destructive to new feature
  records and is used only in isolated pre-release validation.

## Existing entity changes

### User

Existing table: `users`

| Field | Type | Null | Rules |
|---|---|---:|---|
| `profile_picture_url` | varchar(2048) | yes | Set only from a verified, bounded, absolute HTTPS Google-hosted `picture` claim; null triggers the accessible placeholder |

Existing `email`, `display_name`, `role`, `status`, `org_id`, `auth_generation`, and
`registration_domain_mapping_id` remain authoritative.

Revision `005` drops `ck_users_registration_mapping_candidate`. Registration provenance remains
immutable, but an Admin may assign any supported role to a provenance-linked account. This removes
the current schema conflict with FR-027 without erasing how the account was created.

Role transition rules:

1. Lock the target User.
2. Verify the requested role is Candidate, Manager, or Admin.
3. If entering Candidate and no CandidateProfile exists, create one in the same organization.
4. If leaving Candidate, retain CandidateProfile as dormant historical/ownership data.
5. Retain `registration_domain_mapping_id` unchanged.
6. For an actual change, increment `auth_generation`, revoke every live session with
   `ROLE_CHANGED`, append the audit event, and commit once.
7. A same-role request is an idempotent no-op.

Profile refresh rules:

- The signed and verified Google email remains the identity-binding input.
- A usable signed name refreshes `display_name`; absent/unusable name retains the existing safe
  fallback behavior.
- A usable signed picture URL refreshes `profile_picture_url`; unusable or explicitly absent
  picture becomes null so stale third-party images are not shown indefinitely.

## New entities

### JobDescription

Table: `job_descriptions`

| Field | Type | Null | Rules |
|---|---|---:|---|
| `id` | UUID | no | Primary key |
| `org_id` | UUID | no | Tenant; references Organization |
| `created_by_user_id` | UUID | no | Creating Manager; same organization as the JD |
| `title` | varchar(200) | no | Trimmed, normalized whitespace, 1–200 characters |
| `source_type` | varchar(20) | no | `MANUAL` or `UPLOAD` |
| `content_text` | text | no | Normalized nonblank canonical JD text, at most 500,000 characters |
| `source_format` | varchar(10) | yes | Null for manual entry; `PDF`, `DOCX`, or `TXT` for upload |
| `created_at` | timestamptz | no | Creation time |
| `updated_at` | timestamptz | no | Last persistence update; no edit workflow exists in this feature |

Constraints:

- Primary key `pk_job_descriptions` on `id`.
- Foreign key `fk_job_descriptions_organization` from `org_id` to `organizations.id`, delete
  restricted.
- Composite foreign key `fk_job_descriptions_creator_org` from
  `(created_by_user_id, org_id)` to `users(id, org_id)`, delete restricted and organization update
  cascaded.
- Unique `uq_job_descriptions_id_org` on `(id, org_id)`.
- Unique `uq_job_descriptions_id_creator_org` on `(id, created_by_user_id, org_id)` so a scheduled
  interview can prove the selected JD belongs to its scheduling Manager.
- Check `ck_job_descriptions_source_type` allows only `MANUAL` and `UPLOAD`.
- Check `ck_job_descriptions_source_shape` requires `source_format IS NULL` for `MANUAL` and one of
  `PDF|DOCX|TXT` for `UPLOAD`.
- Check `ck_job_descriptions_title_nonblank` and `ck_job_descriptions_content_nonblank` reject
  blank persisted values; API validation enforces upper bounds before persistence.

Indexes:

- `ix_job_descriptions_creator_created_id` on
  `(created_by_user_id, created_at DESC, id DESC)` for Manager-owned pagination.
- `ix_job_descriptions_org_created_id` on `(org_id, created_at DESC, id DESC)` for tenant-safe
  operational queries.
- `ix_job_descriptions_created_id` on `(created_at DESC, id DESC)` for the explicit
  application-wide Admin table.

Creation rules:

- Manual creation normalizes title and supplied text and writes one row with `source_type=MANUAL`.
- Upload creation validates and extracts before opening the persistence write. It writes canonical
  text and format only; original bytes, original filename, and parser details are discarded.
- The authenticated actor must currently be an ACTIVE Manager. The creator ID is derived from the
  authenticated session, never accepted from the request.
- The feature has no update, delete, download, or cross-Manager sharing transition.

### ScheduledInterview

Table: `scheduled_interviews`

| Field | Type | Null | Rules |
|---|---|---:|---|
| `id` | UUID | no | Primary key; also identifies the Candidate allocation |
| `org_id` | UUID | no | Candidate, Manager, and JD tenant at scheduling time |
| `candidate_user_id` | UUID | no | Selected ACTIVE Candidate User |
| `job_description_id` | UUID | no | Selected Manager-owned JD |
| `scheduling_manager_user_id` | UUID | no | Authenticated ACTIVE Manager |
| `scheduled_at` | timestamptz | no | Future absolute instant parsed from RFC 3339 with explicit offset and stored in UTC |
| `status` | varchar(20) | no | Initial and only in-scope value: `SCHEDULED` |
| `idempotency_key_digest` | bytea(32) | no | SHA-256 digest of the submitted opaque key; raw key is never persisted or logged |
| `request_fingerprint` | bytea(32) | no | SHA-256 over canonical Candidate, JD, and scheduled instant for replay comparison |
| `created_at` | timestamptz | no | Scheduling time |
| `updated_at` | timestamptz | no | Last persistence update; no status mutation exists in this feature |

Constraints:

- Primary key `pk_scheduled_interviews` on `id`.
- Foreign key `fk_scheduled_interviews_organization` from `org_id` to `organizations.id`, delete
  restricted.
- Composite foreign key `fk_scheduled_interviews_candidate_org` from
  `(candidate_user_id, org_id)` to `users(id, org_id)`, delete and organization update restricted.
- Composite foreign key `fk_scheduled_interviews_manager_org` from
  `(scheduling_manager_user_id, org_id)` to `users(id, org_id)`, delete and organization update
  restricted.
- Composite foreign key `fk_scheduled_interviews_owned_jd` from
  `(job_description_id, scheduling_manager_user_id, org_id)` to
  `job_descriptions(id, created_by_user_id, org_id)`, delete and organization update restricted.
- Unique `uq_scheduled_interviews_manager_idempotency` on
  `(scheduling_manager_user_id, idempotency_key_digest)`.
- Check `ck_scheduled_interviews_status` allows only `SCHEDULED` in this feature.
- Check `ck_scheduled_interviews_idempotency_digest_length` and
  `ck_scheduled_interviews_fingerprint_length` require 32-byte digests.

Indexes:

- `ix_scheduled_interviews_candidate_scheduled_id` on
  `(candidate_user_id, scheduled_at ASC, id ASC)` for the Candidate home.
- `ix_scheduled_interviews_manager_scheduled_id` on
  `(scheduling_manager_user_id, scheduled_at ASC, id ASC)` for Manager history.
- `ix_scheduled_interviews_org_scheduled_id` on `(org_id, scheduled_at ASC, id ASC)` for tenant
  validation and future operational use.

Scheduling transaction:

1. Derive Manager and organization from the authenticated session and lock the Manager User.
2. Resolve the idempotency digest for that Manager.
3. If a record exists and its fingerprint matches, return it without a second insert/audit.
4. If a record exists and its fingerprint differs, return an idempotency conflict.
5. Lock and validate an ACTIVE Candidate in the same organization.
6. Lock and validate a JD whose `created_by_user_id` is the Manager and whose organization matches.
7. Require a valid offset-bearing timestamp strictly later than the injected current time.
8. Insert one `SCHEDULED` row and append one safe scheduling audit event.
9. Flush and commit at the request transaction boundary. Any error rolls back both row and audit.

No separate allocation table exists: Candidate and Manager list views are projections of this row.

## Read projections

### AuthenticatedUserProjection

- `id`, `organizationId`, `displayName`, `email`, `profilePictureUrl`, `role`, and Candidate profile
  ID when role is Candidate.
- Used by `/auth/me`, the authenticated header, profile page, and role router.

### CandidateInterviewProjection

- Interview `id`, JD `id` and `title`, `scheduledAt`, and `status`.
- Candidate ID, Manager identity, JD content, and idempotency evidence are omitted.
- Query always filters `candidate_user_id` from the authenticated session.

### ManagerCandidateProjection

- Candidate `id`, `displayName`, and `email` only.
- Query filters ACTIVE Candidate role and the Manager's organization.

### ManagerJobDescriptionProjection

- JD `id`, `title`, `sourceType`, `sourceFormat`, and `createdAt`.
- Content is omitted from home-screen lists.

### ManagerInterviewProjection

- Interview `id`; Candidate `id`, `displayName`, and `email`; JD `id` and `title`;
  `scheduledAt`; and `status`.
- Query always filters `scheduling_manager_user_id` from the authenticated session.

### AdminUserProjection

- User `id`, `displayName`, `email`, `role`, `status`, `organizationId`, and nullable
  `profilePictureUrl`; Candidate profile ID may be included in detail but is not required in the
  table projection.
- List is application-wide and never returns identity provider subject/session details.

### AdminJobDescriptionProjection

- JD `id`, `title`, `sourceType`, `sourceFormat`, creator `id` and `displayName`,
  `organizationId`, and `createdAt`.
- Canonical content is omitted.

## Pagination model

All paged endpoints use:

| Field | Rule |
|---|---|
| `page` | Integer, minimum 1, default 1 |
| `pageSize` | Integer, 1–100, default 25 |
| `items` | Minimum role-appropriate projection |
| `totalItems` | Count after the exact authorization/ownership predicate |
| `totalPages` | `ceil(totalItems / pageSize)`; zero when there are no items |

Ordering is deterministic with `id` as the final tie-breaker. The no-skip/no-duplicate guarantee
applies to an unchanged result set, as specified.

## Upload validation model

Before canonical text reaches `JobDescription`:

- Read no more than 5 MiB plus one sentinel byte; a larger stream fails with 413.
- Decode and validate the final extension against `.pdf`, `.docx`, and `.txt`; never use the name
  as a storage path and discard it after validation.
- Compare declared media type with the allowlist but do not trust it as sole evidence.
- PDF: require `%PDF-` signature, reject encrypted content, bound pages and extracted characters,
  and treat parser failures as safe unreadable-document errors.
- DOCX: require a valid ZIP/OpenXML container, reject macro-enabled content, path traversal,
  excessive entries, excessive uncompressed size/compression ratio, and malformed documents before
  bounded extraction.
- TXT: require strict UTF-8, reject NUL/binary content, and normalize line endings/whitespace.
- All formats must yield nonblank normalized content of at most 500,000 characters.
- Parser errors expose only a stable reason category and correlation ID; bytes, filename, title,
  text, and raw exception never enter logs/audits.

## Tenant reassignment and lifecycle invariants

- `JobDescription` is single-owner data and follows its provenance-linked creator's organization
  through the established composite `ON UPDATE CASCADE` contract when no scheduled record blocks
  the move.
- `ScheduledInterview` is multi-owner data. The `scheduled_interviews` migration participant locks
  rows involving any affected User as Candidate or Manager and raises a safe conflict before core
  User organization changes.
- The participant performs no commit, rollback, nested transaction, or external I/O. Its migrate
  count is zero because the valid behavior is either no affected rows or total transaction abort.
- Immediate restrictive foreign keys ensure a missing participant cannot silently create a
  cross-tenant interview.
- Domain removal may disable a provenance-linked account without deleting JDs or interviews;
  role/status checks prevent new access or scheduling and history remains auditable.

## Migration and recovery

Revision `005_add_jds_and_scheduled_interviews`:

1. Adds nullable `users.profile_picture_url`.
2. Drops `ck_users_registration_mapping_candidate`.
3. Creates `job_descriptions` with named constraints/indexes.
4. Creates `scheduled_interviews` after JobDescription and User dependencies.
5. Imports new model modules in Alembic metadata registration.
6. Leaves every existing User's picture null and preserves all revision `004` data.

The isolated downgrade drops `scheduled_interviews`, then `job_descriptions`, restores the old
provenance-role check only after verifying no provenance-linked non-Candidate exists, and drops the
picture column. Because the old check may be incompatible with valid new role assignments and the
new tables contain business data, production rollback uses backup plus a new forward corrective
revision rather than automatic downgrade.
