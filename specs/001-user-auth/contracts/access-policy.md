# Authorization Policy Contract

## Purpose

Define the reusable server-side policy interface supplied by authentication to later Candidate,
JD, allocation, interview, readiness-report, and Admin modules. This feature does not implement
those modules' domain behavior.

## Inputs

### AuthContext

| Field | Required | Meaning |
|---|---:|---|
| `user_id` | yes | Authenticated application User |
| `org_id` | yes | Organization boundary |
| `role` | yes | `CANDIDATE`, `MANAGER`, or `ADMIN` |
| `candidate_profile_id` | Candidate only | One-to-one Candidate profile |
| `session_id` | internal | Safe server-side session identifier |
| `correlation_id` | yes | Request/audit correlation |

### ResourceScope

| Field | Required | Meaning |
|---|---:|---|
| `org_id` | yes | Resource organization |
| `capability` | yes | Explicit requested capability |
| `candidate_owner_user_id` | ownership capabilities | Candidate owner |
| `managing_manager_user_id` | managed readiness capability | Responsible Manager |
| `resource_id` | when available | Safe resource reference for audit |

Missing required scope data produces DENY.

## Capabilities

- `CANDIDATE_VIEW_OWN_PROFILE`
- `CANDIDATE_VIEW_OWN_ALLOCATIONS`
- `CANDIDATE_JOIN_OWN_INTERVIEW`
- `MANAGER_UPLOAD_JD`
- `MANAGER_ALLOCATE_INTERVIEW`
- `MANAGER_VIEW_MANAGED_READINESS`
- `ADMIN_MANAGE_USERS`
- `ADMIN_MANAGE_APPLICATION`
- `ADMIN_VIEW_ALL_REPORTS`

## Decision Order

1. Deny if no valid AuthContext.
2. Deny if AuthContext and ResourceScope organizations differ.
3. Deny if the role lacks the requested capability.
4. For Candidate-owned capabilities, require `candidate_owner_user_id == AuthContext.user_id` and
   the authenticated Candidate profile.
5. For managed readiness, require `managing_manager_user_id == AuthContext.user_id`.
6. Allow only after every applicable condition succeeds.

Authorization is evaluated in or before the resource query so protected data is not fetched and
then filtered in application memory.

## Permission Matrix

| Capability | Candidate | Manager | Admin |
|---|---|---|---|
| View allocated interviews | Own only | Allocation scope only | Allowed |
| View candidate data | Own permitted data only | Allocation scope only | Allowed |
| Upload JD | Denied | Allowed | Allowed |
| Allocate interview | Denied | Allowed | Allowed |
| View managed readiness | Denied | Own managed interviews only | Allowed |
| View all reports | Denied | Denied | Allowed |
| Manage users/roles/status | Denied | Denied | Allowed |

## HTTP Behavior

- Missing/invalid/expired/revoked session: `401` with `SIGN_IN_AGAIN` recovery.
- Valid session lacking capability: `403` with `GO_TO_ROLE_HOME` recovery.
- Cross-organization or ownership mismatch: safe `403` or non-enumerating `404`, selected
  consistently by the consuming resource contract.
- Every denial emits a secret-safe AuditEvent with capability, safe resource reference, reason,
  and correlation ID.
- Navigation visibility never substitutes for this policy.

## Integration Verification

Use test-only FastAPI routers and resource fixtures to prove dependency composition. Do not expose
capability-probe or placeholder protected endpoints in production solely for authentication tests.
The test matrix must include:

- Candidate own versus other Candidate and cross-organization resources.
- Manager managed versus another Manager's readiness resource.
- Manager denial for all-report access.
- Admin allowed capabilities within organization context.
- Missing ownership/manager scope default denial.
