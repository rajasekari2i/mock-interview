# Candidate Tenant Migration Contract

## Purpose

Define how Candidate-owned PostgreSQL modules participate in an Admin domain-mapping reassignment
without partial tenant movement. This contract applies only to data in the application's shared
PostgreSQL transaction boundary. External systems cannot participate and must block reassignment
until a separately approved migration design exists.

## Coordinator Input

| Field | Meaning |
|---|---|
| `session` | The existing request-scoped AsyncSession and transaction |
| `mapping_id` | Locked active OrganizationDomainMapping |
| `candidate_user_ids` | Provenance-linked Candidate UUIDs, sorted deterministically |
| `source_org_id` | Current mapping organization |
| `target_org_id` | Validated active destination organization |
| `actor_user_id` | Authenticated Admin initiating reassignment |
| `correlation_id` | Safe request/audit correlation identifier |
| `now` | One injected UTC operation timestamp |

## Participant Interface

Every Candidate-owned module that cannot migrate solely through a composite ownership FK with
`ON UPDATE CASCADE` registers exactly one participant with:

- a stable, globally unique `name`;
- `validate_and_lock(...)`, which locks affected rows in deterministic order and raises a safe
  conflict before any migration write;
- `migrate(...) -> affected_count`, which updates all owned organization fields using the supplied
  session.

Participants MUST NOT commit, roll back, open a nested transaction, perform external I/O, enqueue
work, or catch and suppress an invariant failure. The registry rejects missing/duplicate production
participant names in contract tests.

## Transaction Order

1. Acquire the transaction advisory lock for the canonical domain.
2. Lock the active mapping, source/target Organizations, and provenance-linked Users.
3. If target equals source, return the current mapping as an idempotent no-op without participant,
   generation, session, or audit mutation.
4. Preflight target email uniqueness and mapping state.
5. Invoke every participant's `validate_and_lock` in stable name order.
6. Update mapping and locked User organization IDs; ownership FKs cascade simple auth rows.
7. Invoke every participant's `migrate` in the same stable order.
8. Increment each affected User auth generation and revoke active sessions with
   `DOMAIN_MAPPING_REASSIGNED`.
9. Append aggregate mapping and per-Candidate safe audit events.
10. Flush and commit once at the request transaction boundary.

Any failure rolls back every step. Historical AuditEvents are immutable and remain associated with
the organization in which they originally occurred.

## Locking Rules

- Canonical-domain advisory lock is always first.
- Mapping and Organization rows precede User and participant rows.
- Users and participant records are locked by ascending UUID/primary key.
- Registration uses the same advisory/mapping lock order, so it observes one complete mapping
  state before or after a mutation.
- Tests use bounded PostgreSQL lock/statement timeouts and two independent sessions to prove
  blocking and final-state consistency.

## Failure Contract

- Target organization missing/disabled: safe not-found/conflict; no writes.
- Target organization equals source: idempotent success; no migration or security-state mutation.
- Target `(org_id, normalized_email)` collision: conflict; no merge or identity rebinding.
- Participant validation/migration failure: safe tenant-migration conflict; complete rollback.
- Registry omission/duplication: startup or contract-test failure; reassignment is not released.
- External/non-transactional Candidate data: reassignment blocked until an approved participant or
  migration boundary exists.

## Verification

- Success fixture migrates auth rows plus a synthetic Candidate-owned participant table.
- Injected participant failure proves mapping, Users, profiles, identities, sessions, fixture data,
  generations, and audit rows are unchanged.
- Independently pre-provisioned same-domain Users remain unchanged.
- Removed mapping provenance is never reused by a later mapping incarnation for the same domain.
