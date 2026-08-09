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

- Has many Users, CandidateProfiles, AuthenticationSessions, and AuditEvents.
- V1 seeds one development organization; the schema remains tenancy-ready.

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
| `created_at` | timestamptz | Required |
| `updated_at` | timestamptz | Required |

Constraints and invariants:

- Unique `(org_id, normalized_email)`.
- Exactly one role per User.
- Public/self-registration is absent; Admin provisioning is authoritative.
- Changing role or disabling the User increments `auth_generation`, revokes all active sessions,
  and writes an AuditEvent in the same transaction.
- Re-enabling does not decrement generation or restore a session.
- A Candidate may become active only after a valid same-organization CandidateProfile association
  exists. The service enforces this role-conditional invariant transactionally.

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
- First binding selects one active, unbound, pre-provisioned User by verified normalized email in
  the single v1 organization and inserts the identity atomically.
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
  supported by the migration.
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
- `IDENTITY_BOUND`, `IDENTITY_BINDING_DENIED`
- `CANDIDATE_PROFILE_LINKED`, `CANDIDATE_PROFILE_LINK_DENIED`
- `AUTHORIZATION_DENIED`

Audit rows are append-only through the application API. Tokens, cookie values, authorization
codes, raw state/nonce, provider payloads, and unnecessary email/claim values are prohibited.

## Typed Authorization Inputs (non-persistent)

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

## State Transitions

### User

```text
Admin provisions -> ACTIVE or DISABLED
ACTIVE --disable--> DISABLED + generation++ + revoke all
DISABLED --enable--> ACTIVE (old sessions stay revoked)
role A --change--> role B + generation++ + revoke all
```

A transition to Candidate requires the CandidateProfile invariant before commit. A transition
away from Candidate is rejected with `CANDIDATE_PROFILE_CONFLICT` while the profile exists; the
transaction makes no role, generation, session, or audit mutation.

### External identity

```text
unbound pre-provisioned User --verified first login--> bound Google identity
bound identity --matching subject login--> authenticated
bound identity --email drift--> authenticated by subject; snapshot may update safely
collision/ambiguous email/replay --> denied + audited
```

### Session

```text
ACTIVE -> IDLE_EXPIRED | ABSOLUTE_EXPIRED | REVOKED
```

Expired or revoked states are terminal. Global events revoke every active row and increment the
User generation.

## Migration and Recovery

- One reviewed initial Alembic migration creates all authentication tables, named constraints, and
  indexes.
- Migration tests run upgrade base→head, constraint/collision checks, downgrade head→base in an
  isolated database, and upgrade again.
- Production recovery prefers a forward corrective migration after deployment; the downgrade is
  documented and tested for non-production/release rollback use.
- Development seed data is idempotent and separate from migrations; it contains no production
  identity or secret.
