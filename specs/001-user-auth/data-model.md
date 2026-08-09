# Data Model: User Authentication and Role Access

## Conventions

- PostgreSQL UUID primary keys.
- Timezone-aware UTC timestamps.
- Explicitly named foreign keys, unique constraints, checks, and indexes.
- Every owned record carries `org_id` or is reachable through a constrained organization-owned
  parent.
- Role and status values use checked strings for migration portability.
- Secrets and raw OAuth/session credentials are never persisted.

## Organization

| Field | Type | Rules |
|---|---|---|
| `id` | UUID | Primary key |
| `name` | text | Required, non-empty |
| `slug` | text | Required, globally unique, normalized |
| `status` | text | `ACTIVE` or `DISABLED` |
| `created_at` | timestamptz | Required |
| `updated_at` | timestamptz | Required |

Relationships:

- Has many OrganizationDomainMappings, Users, CandidateProfiles, AuthenticationSessions, and
  AuditEvents.

## OrganizationDomainMapping

| Field | Type | Rules |
|---|---|---|
| `id` | UUID | Primary key; stable mapping-incarnation identifier |
| `org_id` | UUID | Required FK to active target Organization; delete restricted |
| `normalized_domain` | varchar(253) | Required canonical IDNA ASCII, lowercase, exact-match value |
| `created_at` | timestamptz | Required |
| `updated_at` | timestamptz | Required |
| `removed_at` | timestamptz | Nullable; non-null means unavailable for registration |

Constraints and invariants:

- Partial unique index on `normalized_domain WHERE removed_at IS NULL`: at most one active mapping
  per exact domain while preserving removed mapping incarnations and their provenance.
- Wildcards, URLs, `@`, empty/invalid labels, and implicit parent/subdomain matches are rejected.
- Removal is soft; removed rows cannot be reassigned or used for login registration.
- Create, remove, reassign, and first-login registration acquire the same transaction advisory lock
  for the canonical domain before reading or mutating a mapping.
- Reassignment updates `org_id` only after target-organization and migration preflight succeeds.
- Reassignment to the current `org_id` is an idempotent no-op with no participant, generation,
  session, timestamp, or audit mutation.

## User

| Field | Type | Rules |
|---|---|---|
| `id` | UUID | Primary key |
| `org_id` | UUID | Required FK to Organization |
| `email` | text | Required display/canonical email |
| `normalized_email` | text | Required normalized lookup value |
| `display_name` | text | Required, non-empty |
| `role` | text | `CANDIDATE`, `MANAGER`, or `ADMIN` |
| `status` | text | `ACTIVE` or `DISABLED` |
| `auth_generation` | bigint | Required, starts at 1, increases on global revocation |
| `registration_domain_mapping_id` | UUID | Nullable FK to OrganizationDomainMapping, delete restricted |
| `created_at` | timestamptz | Required |
| `updated_at` | timestamptz | Required |

Constraints and invariants:

- Unique `(org_id, normalized_email)`.
- Exactly one role per User.
- Null `registration_domain_mapping_id` means independently pre-provisioned. A non-null value is
  immutable provenance for a self-registered Candidate and requires role `CANDIDATE`.
- A verified exact active domain mapping may create an active Candidate atomically; Manager/Admin
  roles remain Admin-provisioned and cannot be selected during registration.
- Changing role or disabling the User increments `auth_generation`, revokes all active sessions,
  and writes an AuditEvent in the same transaction.
- Re-enabling does not decrement generation or restore a session.
- A Candidate may become active only after a valid same-organization CandidateProfile association
  exists. The service enforces this role-conditional invariant transactionally.
- Mapping reassignment preflights target `(org_id, normalized_email)` uniqueness, updates the User
  tenant, increments generation, cascades owned authentication rows, and revokes all sessions.

## ExternalLoginIdentity

| Field | Type | Rules |
|---|---|---|
| `id` | UUID | Primary key |
| `org_id` | UUID | Required; must match User organization |
| `user_id` | UUID | Required FK to User |
| `provider` | text | Required; v1 value `GOOGLE` |
| `issuer` | text | Required normalized issuer |
| `subject` | text | Required stable provider subject |
| `email_snapshot` | text | Optional safe operational snapshot; never an authorization key after binding |
| `bound_at` | timestamptz | Required |
| `last_authenticated_at` | timestamptz | Required |

Constraints and invariants:

- Unique `(provider, issuer, subject)`.
- Unique `(user_id, provider)`; one Google identity per User in v1.
- First binding selects exactly one active, unbound, pre-provisioned User by verified normalized
  email across organizations without requiring a mapping; multiple matches deny. Only no match
  proceeds to exact-domain mapping and atomic Candidate creation.
- Concurrent or conflicting bindings fail closed and produce a safe AuditEvent.
- Later logins resolve by `(issuer, subject)` only; email change never auto-rebinds.

## CandidateProfile

| Field | Type | Rules |
|---|---|---|
| `id` | UUID | Primary key |
| `org_id` | UUID | Required FK to Organization |
| `user_id` | UUID | Required unique FK to User |
| `created_at` | timestamptz | Required |
| `updated_at` | timestamptz | Required |

Constraints and invariants:

- Unique `user_id`: at most one profile per User and one User per profile.
- CandidateProfile and User must share `org_id`; enforce with a composite FK/unique parent key where
  supported by the migration and `ON UPDATE CASCADE` for tenant reassignment.
- The linked User must have role `CANDIDATE`; transactional service validation enforces this
  role-conditional rule.
- Candidate provisioning creates/associates the profile before the User becomes active.
- V1 rejects changing a Candidate User to Manager/Admin while the CandidateProfile exists. Profile
  archival/deletion is a separate Candidate-lifecycle decision and is not performed implicitly.
- Profile-photo data and editing are outside this feature.

## AuthenticationSession

| Field | Type | Rules |
|---|---|---|
| `id` | UUID | Primary key; safe internal correlation identifier |
| `org_id` | UUID | Required; must match User organization |
| `user_id` | UUID | Required FK to User |
| `token_digest` | bytea/text | Required globally unique SHA-256 digest; raw token never stored |
| `csrf_token_digest` | bytea/text | Required SHA-256 digest; raw CSRF token exists only in readable CSRF cookie |
| `auth_generation` | bigint | Snapshot of User generation at creation |
| `created_at` | timestamptz | Required |
| `last_activity_at` | timestamptz | Required |
| `absolute_expires_at` | timestamptz | Required; `created_at + 8 hours` |
| `idle_expires_at` | timestamptz | Required; initially `created_at + 2 hours` |
| `revoked_at` | timestamptz | Nullable |
| `revocation_reason` | text | Nullable checked safe enum |
| `updated_at` | timestamptz | Required |

Revocation reasons:

- `LOGOUT_ALL`
- `ROLE_CHANGED`
- `ACCOUNT_DISABLED`
- `ABSOLUTE_EXPIRED`
- `IDLE_EXPIRED`
- `SECURITY_REVOKED` (reserved for a reviewed future Admin incident operation)
- `DOMAIN_MAPPING_REMOVED`
- `DOMAIN_MAPPING_REASSIGNED`

Validation on every authenticated request:

1. Hash the cookie token and resolve the digest.
2. Require `revoked_at IS NULL`.
3. Require current time before both expiry values.
4. Require User and Organization active.
5. Require session generation equal to User generation.
6. Require organization equality.
7. Update `last_activity_at` and set `idle_expires_at` to the earlier of two hours from now and the
   absolute expiry.

Indexes:

- Unique `token_digest`.
- `(user_id, revoked_at)` for global revocation/history.
- `absolute_expires_at` and `idle_expires_at` for cleanup.

## OAuthTransaction

| Field | Type | Rules |
|---|---|---|
| `id` | UUID | Primary key |
| `state_digest` | bytea/text | Required globally unique digest |
| `nonce_digest` | bytea/text | Required digest |
| `pkce_verifier_ciphertext` | bytea/text | Required Fernet/MultiFernet ciphertext |
| `encryption_key_id` | text | Required non-secret rotation-key identifier |
| `return_path` | text | Required allowlisted relative path or fixed default |
| `created_at` | timestamptz | Required |
| `expires_at` | timestamptz | Required short lifetime |
| `consumed_at` | timestamptz | Nullable; one-time callback marker |

Constraints and invariants:

- Raw state/nonce are never logged.
- PKCE ciphertext is decrypted only during callback using validated environment-supplied current or
  previous rotation keys; plaintext exists only in process memory for the exchange.
- Callback consumes the row atomically; replay is denied.
- Expired rows cannot be used and are cleanup candidates.
- The return path cannot contain an external scheme/host.

## AuditEvent

| Field | Type | Rules |
|---|---|---|
| `id` | UUID | Primary key |
| `org_id` | UUID | Nullable for unknown/unprovisioned identity denials |
| `actor_user_id` | UUID | Nullable FK to User |
| `target_user_id` | UUID | Nullable FK to User |
| `event_type` | text | Required checked safe enum |
| `outcome` | text | `SUCCESS` or `DENIED` |
| `reason_code` | text | Required safe enum/code |
| `resource_type` | text | Nullable allowlisted type |
| `resource_id` | UUID/text | Nullable safe identifier |
| `correlation_id` | text | Required opaque request identifier |
| `metadata` | jsonb | Required default `{}`; allowlisted non-secret keys only |
| `occurred_at` | timestamptz | Required, immutable |

Required event types:

- `LOGIN_SUCCEEDED`, `LOGIN_DENIED`
- `LOGOUT_ALL`
- `SESSION_EXPIRED`, `SESSIONS_REVOKED`
- `USER_PROVISIONED`, `USER_STATUS_CHANGED`, `USER_ROLE_CHANGED`
- `CANDIDATE_SELF_REGISTERED`
- `ORG_DOMAIN_MAPPING_CREATED`, `ORG_DOMAIN_MAPPING_REMOVED`, `ORG_DOMAIN_MAPPING_REASSIGNED`
- `CANDIDATE_ORGANIZATION_CHANGED`
- `IDENTITY_BOUND`, `IDENTITY_BINDING_DENIED`
- `CANDIDATE_PROFILE_LINKED`, `CANDIDATE_PROFILE_LINK_DENIED`
- `AUTHORIZATION_DENIED`

Audit rows are append-only through the application API. Tokens, cookie values, authorization
codes, raw state/nonce, provider payloads, and unnecessary email/claim values are prohibited.

## Typed Authorization Inputs (non-persistent)

### VerifiedGoogleClaims

- `issuer`: validated exact HTTPS issuer
- `subject`: non-empty stable Google subject
- `email`: syntactically validated and normalized verified email
- `name`: optional provider-signed display name after Unicode/whitespace/control/length validation

When `name` is absent or unusable, self-registration uses the validated email local part. Provider
payloads and rejected values are never persisted in audit metadata or logs.

### AuthContext

- `user_id`
- `org_id`
- `role`
- `candidate_profile_id` required only for Candidate
- `session_id` internal only
- `correlation_id`

### ResourceScope

- `org_id`
- `capability`
- optional `candidate_owner_user_id`
- optional `managing_manager_user_id`
- optional `resource_id`

Policies always require organization equality, then role/capability, then applicable owner/manager
equality. Missing scope data never produces an allow decision.

## Tenant Migration Participant (non-persistent)

Each Candidate-owned PostgreSQL module that cannot rely solely on ownership-FK cascades registers
exactly one typed participant:

- stable unique `name`;
- `validate_and_lock(session, candidate_user_ids, source_org_id, target_org_id)`;
- `migrate(session, candidate_user_ids, source_org_id, target_org_id, now) -> affected_count`.

The coordinator supplies one AsyncSession and transaction. Participants lock rows in deterministic
order, perform no commit, rollback, external I/O, or nested transaction, and raise on any conflict.
Any exception rolls back mapping, Users, all participants, session revocation, and new audit events.
Simple future Candidate-owned tables SHOULD use a single composite ownership FK with
`ON UPDATE CASCADE`; tables with business invariants MUST also register a participant.

## State Transitions

### User

```text
Admin provisions -> ACTIVE or DISABLED
mapped verified first login -> ACTIVE CANDIDATE + profile + identity + provenance
ACTIVE --disable--> DISABLED + generation++ + revoke all
DISABLED --enable--> ACTIVE (old sessions stay revoked)
role A --change--> role B + generation++ + revoke all
self-registered Candidate --mapping removed--> DISABLED + generation++ + revoke all
self-registered Candidate --mapping reassigned--> new organization + generation++ + revoke all
```

A transition to Candidate requires the CandidateProfile invariant before commit. A transition
away from Candidate is rejected with `CANDIDATE_PROFILE_CONFLICT` while the profile exists; the
transaction makes no role, generation, session, or audit mutation.

### External identity

```text
unbound pre-provisioned User --verified first login--> bound Google identity
unmapped new identity --verified mapped domain--> self-registered Candidate + bound identity
bound identity --matching subject login--> authenticated
bound identity --email drift--> authenticated by subject; snapshot may update safely
collision/ambiguous email/replay --> denied + audited
```

### Organization domain mapping

```text
absent --Admin create--> ACTIVE
ACTIVE --Admin remove--> REMOVED + disable provenance-linked Candidates + revoke all
ACTIVE --Admin reassign--> ACTIVE in target organization + migrate linked Candidates/data + revoke all
REMOVED --> terminal provenance row
```

Create/remove/reassign and first-registration serialize on the canonical-domain advisory lock.
Reassignment failure leaves the mapping and every participant unchanged.

### Session

```text
ACTIVE -> IDLE_EXPIRED | ABSOLUTE_EXPIRED | REVOKED
```

Expired or revoked states are terminal. Global events revoke every active row and increment the
User generation.

## Migration and Recovery

- Preserve implemented revision `001`; add forward revision `002`.
- Revision `002` creates `organization_domain_mappings`, its partial active-domain index, nullable
  User provenance FK/index/check, and the two new session revocation check values.
- Revision `002` drops/recreates `fk_candidate_profiles_user_org`,
  `fk_external_identity_user_org`, and `fk_authentication_sessions_user_org` with
  `ON UPDATE CASCADE`. Existing rows receive null provenance and remain independently provisioned.
- Migration tests populate revision `001`, upgrade to `002`, prove unchanged users, active-domain
  uniqueness, provenance restrictions, and tenant cascades; then downgrade in isolation and
  re-upgrade.
- Production recovery uses a new forward corrective migration. Downgrade is for isolated
  pre-release validation only and cannot preserve mapping/provenance added after `002`.
- Development seed tooling remains idempotent and gains explicit organization-domain mapping input;
  mappings never contain production identity or secrets.
