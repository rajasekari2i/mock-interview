# Feature Specification: User Authentication and Role Access

**Feature Branch**: `001-user-auth`

**Created**: 2026-08-09

**Status**: Plan approved by explicit review-gate override; tasks generated; implementation pending

**Input**: Authentication-only requirements derived from `docs/MockInterview_PRD.md`, covering
registration, Google OAuth2 login, logout, manual-password management, sessions, the Candidate,
Admin, and Manager roles, user identity, and authentication errors.

## Clarifications

### Session 2026-08-09

- Q: Which events should invalidate every active session for a user? → A: Every logout invalidates every session across all devices; role changes also invalidate all active sessions.
- Q: What recovery guidance should users receive for authentication and session failures? → A: Expired or logged-out sessions direct users to sign in again; unprovisioned or disabled accounts direct users to contact an Admin; Google/provider failures direct users to retry.
- Q: Should Managers have access to readiness reports for interviews they manage? → A: Managers may access readiness reports only for interviews they manage; all other report access remains Admin-only.
- Q: How should Google identities and Candidate profiles be linked to application users? → A: One stable Google subject identifier maps to exactly one User, and each Candidate User maps to exactly one Candidate profile.
- Q: What measurable performance target should authenticated API requests meet under expected load? → A: V1 has no fixed throughput or latency acceptance threshold; representative baseline measurements will guide a later target.
- Q: Which organization should automatically registered Candidates join? → A: Map approved Google email domains to existing organizations.
- Q: What should happen when a new user's verified Google email domain has no approved organization mapping? → A: Deny registration with ACCESS_NOT_PROVISIONED and direct the user to contact an administrator.
- Q: How should administrators create and maintain approved email-domain-to-organization mappings? → A: Store mappings in PostgreSQL and manage them through authorized, audited Admin-only API operations.
- Q: How should the required display name be initialized for a newly registered Candidate? → A: Use Google's signed name claim, with a validated email local-part fallback when no usable name is supplied.
- Q: What should removing a domain mapping do to Candidates who already registered through that mapping? → A: Atomically disable Candidates registered through that mapping and revoke all of their active sessions.
- Q: How should an Admin move an approved email domain from one organization to another? → A: Reassign the mapping and migrate existing Candidates registered through it to the new organization.
- Q: What should happen to active sessions when Candidates are migrated through domain reassignment? → A: Revoke every affected Candidate's active sessions and require a fresh Google login.
- Q: How should domain reassignment handle Candidate-owned organization-scoped data outside authentication? → A: Atomically migrate all Candidate-owned organization-scoped data to the new organization.
- Q: How should approved email domains match a new user's verified Google email domain? → A: Require an exact, case-insensitive normalized domain match; subdomains require separate mappings.
- Q: What consistency should apply when first-login registration races with removal or reassignment of the same domain mapping? → A: Serialize both operations transactionally so registration observes one complete mapping state.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sign In with Google (Priority: P1)

As an authorized MockInterview user, I sign in using my Google identity so that the application
can identify me and present the work permitted for my assigned role.

**Why this priority**: The PRD requires Google login for all users, and no protected application
journey is available without authentication.

**Independent Test**: Use authorized Google identities for each of the three roles and verify that
each successful sign-in establishes the correct application identity and role-specific entry view.

**Acceptance Scenarios**:

1. **Given** an authorized Candidate identity, **When** the Candidate successfully signs in with
   Google, **Then** the Candidate is authenticated and sees only allocated interviews.
2. **Given** an authorized Admin identity, **When** the Admin successfully signs in with Google,
   **Then** the Admin is authenticated and can enter the overall application-management area.
3. **Given** an authorized Manager identity, **When** the Manager successfully signs in with
   Google, **Then** the Manager is authenticated and can enter the JD upload and interview
   allocation area.
4. **Given** a Google sign-in that does not complete successfully, **When** control returns to
   MockInterview, **Then** no authenticated access is granted and the user receives a safe error or
   recovery path.
5. **Given** a new user whose verified Google email domain has an approved organization mapping,
   **When** the user completes Google sign-in for the first time, **Then** an active User and
   Candidate profile are created atomically in that organization with the Candidate role.
6. **Given** a new user whose verified Google email domain has no approved organization mapping,
   **When** the user completes Google sign-in, **Then** registration is denied with safe
   contact-Admin recovery and no User, Candidate profile, identity, or session is created.
7. **Given** an Admin removes an approved organization domain mapping, **When** the operation
   commits, **Then** Candidates registered through that mapping are disabled and all their active
   sessions are revoked atomically while independently pre-provisioned users remain unchanged.
8. **Given** an Admin reassigns an approved domain mapping to another organization, **When** the
   operation commits, **Then** every Candidate registered through that mapping and the Candidate's
   required profile, identity associations, and Candidate-owned organization-scoped data move
   atomically to the new organization while independently pre-provisioned users remain unchanged,
   every affected active session is revoked, and each migrated Candidate must sign in again. If
   any affected record cannot migrate, the mapping and all affected records remain unchanged.
9. **Given** first-login registration races with removal or reassignment of the matching domain,
   **When** both operations execute, **Then** they are serialized so registration observes either
   the complete mapping state before the mutation or the complete state after it, never a partial
   tenant transition.

---

### User Story 2 - Enforce Role Permissions (Priority: P1)

As a signed-in user, I can access only the information and actions assigned to my role so that
candidate information, interviews, and reports are protected from unauthorized access.

**Why this priority**: The PRD defines role-specific access as part of authentication and requires
candidates to see no pages beyond their allocated interviews.

**Independent Test**: Exercise the same protected information and actions as Candidate, Admin, and
Manager and compare every result with the role permission matrix in this specification.

**Acceptance Scenarios**:

1. **Given** an authenticated Candidate, **When** the Candidate navigates or requests protected
   content, **Then** only the Candidate's own allocated interviews and own permitted data are
   available, and all other application pages and data are denied.
2. **Given** an authenticated Admin, **When** the Admin accesses application management or reports,
   **Then** full application-management access and all reports are available.
3. **Given** an authenticated Manager, **When** the Manager accesses authentication-protected
   functions, **Then** JD upload, interview allocation, and readiness reports for interviews they
   manage are available, while Admin-only management and all other reports are denied.
4. **Given** any authenticated user, **When** the user attempts an action or data access outside
   their role, **Then** the attempt is denied without exposing the protected content.

---

### User Story 3 - End and Govern Sessions (Priority: P2)

As an authenticated user, I can end my signed-in session and understand when authentication is no
longer valid so that access does not continue unintentionally.

**Why this priority**: Logout and session handling are required for a complete authentication
feature, but the PRD does not define their policy.

**Independent Test**: Under the approved session policy, verify explicit logout, expiry,
revocation, and return-to-protected-content behavior for all three roles.

**Acceptance Scenarios**:

1. **Given** an authenticated user, **When** the user logs out, **Then** protected information is no
   longer accessible through the ended session.
2. **Given** a session that is no longer valid under the approved policy, **When** the user requests
   protected content, **Then** access is denied and the user is directed to authenticate again.
3. **Given** an authentication or session error, **When** the user is informed of the failure,
   **Then** the message does not reveal sensitive account details and directs the user to sign in
   again for expired or logged-out sessions, contact an Admin for unprovisioned or disabled
   accounts, or retry for a Google/provider failure.

---

### User Story 4 - Use Google-Only Authentication (Priority: P3)

As a MockInterview user, I authenticate through the approved Google identity provider without an
unsupported application password surface.

**Why this priority**: The requested feature scope mentions manual login, but the PRD requires
Google login for all users and contains no manual-login or password-management requirement.

**Independent Test**: Verify the API contract and rendered authentication views expose no password
login, password creation, change, forgotten-password, reset, expiry, or lockout journey.

**Acceptance Scenarios**:

1. **Given** any Candidate, Admin, or Manager reaches an authentication view, **When** the view is
   rendered, **Then** Google sign-in is the only authentication method offered.
2. **Given** any user requests a password login or password-management route, **When** the request
   is handled, **Then** no such application route or credential journey is available.

### Edge Cases

- A Google identity is valid but its verified email domain has no approved organization mapping.
- An Admin removes a domain mapping while Candidates registered through it have active sessions.
- An Admin reassigns a domain mapping while Candidates registered through it have active sessions
  or organization-scoped data.
- A Google subject identifier is already associated with another application user or a Candidate
  User is already associated with another Candidate profile; the conflicting association is denied.
- A user's assigned role changes while the user has an active session.
- A Candidate has no allocated interviews at login.
- A Candidate attempts to access another candidate's interview or personal data through a direct
  link or repeated request.
- A Manager attempts to access Admin-only application management or reports.
- Google sign-in is cancelled, denied, unavailable, or returns incomplete identity information.
- A session is logged out, expired, revoked, or otherwise invalid while protected content is open.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A new user whose verified Google email domain has an approved mapping to an existing
  active organization MUST be registered atomically on first Google login as an active Candidate
  User with exactly one Candidate profile in that organization. Admin and Manager roles MUST still
  be assigned through an authorized administrative operation and MUST NOT be selected during
  self-registration. If the verified email domain has no approved organization mapping, the system
  MUST deny registration with `ACCESS_NOT_PROVISIONED` and direct the user to contact an Admin. A
  new Candidate's display name MUST use the validated, provider-signed Google `name` claim when it
  is usable and otherwise fall back to the validated local part of the verified email address. A
  registration domain MUST match an approved mapping exactly after case-insensitive normalization;
  a parent-domain mapping MUST NOT authorize a subdomain, which requires its own explicit mapping.
- **FR-002**: The system MUST allow every authorized Candidate, Admin, and Manager to log in using a
  Google account through Google OAuth2.
- **FR-003**: A successful login MUST resolve one stable Google subject identifier to exactly one
  MockInterview User and application role before protected access is granted; a Google subject
  identifier MUST NOT be associated with more than one User. First-login registration MUST bind
  the verified Google subject in the same transaction that creates the Candidate User and profile.
- **FR-004**: The authentication feature MUST recognize the three roles defined by PRD FR-1:
  Candidate, Admin, and Manager.
- **FR-005**: An authenticated Candidate MUST see only interviews allocated to that Candidate, MUST
  see only that Candidate's permitted data, and MUST NOT see other application pages.
- **FR-006**: An authenticated Admin MUST be able to manage the overall application and have full
  access to reports.
- **FR-007**: An authenticated Manager MUST be able to upload JDs, allocate interviews to
  candidates, and access readiness reports only for interviews that Manager manages.
- **FR-008**: Every protected action and data request MUST enforce the authenticated user's role and
  identity; unavailable navigation alone MUST NOT be treated as permission enforcement.
- **FR-009**: Failed, cancelled, incomplete, or unauthorized login attempts MUST NOT create
  authenticated access or reveal protected information.
- **FR-010**: An application session MUST have an 8-hour maximum lifetime and a 2-hour idle timeout.
  No fixed concurrent-session limit applies. Explicit logout MUST invalidate every active session
  for that user across all devices, and any role change MUST also invalidate every active session
  for the affected user. Disabling a user MUST invalidate every active session and prevent future
  authenticated use until the account is enabled again.
- **FR-011**: Google OAuth2 MUST be the only v1 login method; the system MUST NOT expose application
  username/password login or password creation, change, recovery, reset, expiry, or lockout flows.
- **FR-012**: When authentication or authorization fails, the system MUST deny protected access,
  preserve any existing protected data from disclosure, avoid revealing sensitive account
  details, and provide category-specific recovery guidance: expired or logged-out sessions MUST
  direct the user to sign in again; unprovisioned or disabled accounts MUST direct the user to
  contact an Admin; and Google/provider failures MUST direct the user to retry.
- **FR-013**: Logging out or reaching any other approved session-ending condition MUST prevent that
  ended session from accessing protected information.
- **FR-014**: Each Candidate User MUST be associated with exactly one Candidate profile used by the
  interview-start identity check, and each Candidate profile MUST be associated with exactly one
  Candidate User; the profile-photo comparison itself remains outside this authentication feature.
- **FR-015**: Authentication and authorization outcomes for sensitive or denied access MUST be
  auditable without recording credentials, authentication secrets, or unnecessarily sensitive
  identity data.
- **FR-016**: Login, authentication errors, protected-route errors, and session-expiry interfaces
  MUST meet WCAG 2.2 AA, including keyboard operation, visible focus, semantic labels, sufficient
  contrast, and screen-reader error or status announcements.
- **FR-017**: Approved organization domain mappings MUST be persisted in PostgreSQL and managed
  only through authenticated Admin API operations. Creating, changing, or removing a mapping MUST
  be authorized server-side, reject a domain mapped to more than one organization, and emit a safe
  audit event without recording credentials or authentication tokens. Removing a mapping MUST
  atomically disable every Candidate registered through that mapping and revoke all of their active
  sessions; it MUST NOT affect users who were pre-provisioned independently of that mapping.
  Reassigning a mapping to another organization MUST atomically move every Candidate registered
  through that mapping, including the required Candidate profile and external identity tenant
  associations, to the new organization without moving independently pre-provisioned users. The
  reassignment MUST revoke every active session for each migrated Candidate and require a fresh
  login before the Candidate can access the new organization. It MUST also migrate all
  Candidate-owned organization-scoped data across participating modules in the same atomic
  operation; if any affected record cannot migrate, the mapping reassignment and every related
  mutation MUST roll back. First-login registration and mutation of its matching domain mapping
  MUST be transactionally serialized so registration observes exactly one complete mapping state
  and cannot commit against a stale or partially changed tenant association.

### Permission Matrix

| Capability | Candidate | Admin | Manager |
|------------|-----------|-------|---------|
| Log in with Google | Allowed | Allowed | Allowed |
| View allocated interviews | Own allocations only | Overall management access | As needed for allocation |
| View candidate data | Own permitted data only | Full application-management scope | Only scope required to allocate interviews |
| Upload JDs | Denied | Available through overall management | Allowed |
| Allocate interviews | Denied | Available through overall management | Allowed |
| Access managed-interview readiness reports | Denied | Allowed | Own managed interviews only |
| Access all reports | Denied | Allowed | Not stated; therefore denied in this feature |
| Access other application pages | Denied | Allowed within full management scope | Only JD upload and allocation areas stated |

### Scope Boundaries

In scope:

- Admin pre-provisioning of organization-bound users and one assigned v1 role.
- First-login Candidate self-registration through approved Google email-domain-to-organization
  mappings.
- Admin-only management of persisted organization domain mappings.
- Google OAuth2 login for Candidate, Admin, and Manager.
- Logout, authentication-session lifecycle, role enforcement, user identity association, and
  authentication or authorization errors.

Out of scope:

- Candidate profile editing, interview execution, proctoring, scoring, reporting behavior, JD
  processing, and scheduling except where their entry points require role authorization.
- The interview-start photo and liveness comparison; authentication only supplies the associated
  Candidate identity.
- Mentor, Reviewer, Program Owner, Staffing/Sales Coordinator, and Question-Bank Curator permission
  models. The requested scope is limited to the three roles explicitly defined in PRD FR-1.
- Username/password registration, authentication, and password management.

### Key Entities *(include if feature involves data)*

- **User Identity**: The person recognized by MockInterview, including the assigned application
  role, a validated display name, and, for Candidates, a required one-to-one association with a
  Candidate profile.
- **External Login Identity**: The stable Google subject identifier presented for login and its
  required one-to-one association with one MockInterview User.
- **Organization Domain Mapping**: A persisted, globally unique association from a normalized
  Google email domain to one existing organization, managed through authorized and audited Admin
  operations and used only to place first-login Candidate registrations. Each self-registered
  Candidate retains immutable provenance to the mapping used for registration so removal can
  disable exactly the affected accounts and revoke their sessions, and reassignment can migrate
  exactly those accounts to the new organization. Matching is exact after case-insensitive
  normalization; parent domains do not implicitly include subdomains.
- **Role Assignment**: The user's Candidate, Admin, or Manager authority and the corresponding
  allowed actions and data scope.
- **Authentication Session**: The bounded period during which a successfully authenticated user
  may access protected capabilities, with an 8-hour maximum lifetime and 2-hour idle timeout. V1
  has no fixed concurrent-session limit; logout, role change, or account disablement invalidates
  all active sessions for the affected user.
- **Authentication Event**: An auditable login, logout, session, or denied-access outcome that
  excludes secrets and unnecessary identity data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In acceptance testing, 100% of authorized Google identities for Candidate, Admin, and
  Manager can complete login and are assigned the expected application identity and role.
- **SC-002**: Across the permission matrix, 100% of allowed role-action combinations succeed and
  100% of denied combinations are blocked without exposing protected content.
- **SC-003**: In all Candidate access tests, Candidates can access their own allocated interviews
  and permitted data, while zero other application pages, other candidates' interviews, or other
  candidates' data are exposed.
- **SC-004**: In all tested failed, cancelled, incomplete, unauthorized, expired, revoked, and
  logged-out cases covered by the approved policy, protected access is denied and the user receives
  the approved safe recovery guidance.
- **SC-005**: In all tested logout and session-ending cases, the ended session succeeds in zero
  subsequent protected requests.
- **SC-006**: Manual login and password-management entry points are absent from 100% of API contract
  and rendered authentication-view checks.
- **SC-007**: Security and privacy review finds zero unresolved critical or high-severity issues in
  registration, login, logout, session handling, password handling, identity association, or role
  enforcement before release.
- **SC-008**: Automated accessibility checks report zero WCAG 2.2 AA violations in authentication
  views, and the documented keyboard and screen-reader checks pass for login, errors, protected
  routes, and session expiry.
- **SC-009**: Before release, a representative authentication API load test records sustained
  throughput plus p50 and p95 latency as a non-blocking baseline; v1 has no fixed throughput or
  latency acceptance threshold until production usage is measured.
- **SC-010**: In first-login registration tests, 100% of new users with an approved domain mapping
  are created in the mapped organization as Candidates with exactly one profile and identity, while
  100% of users without a mapping are denied and leave no partial registration records.
- **SC-011**: In domain-mapping authorization and lifecycle tests, 100% of non-Admin mutations are
  denied; every successful removal disables exactly the Candidates registered through that mapping,
  revokes all their active sessions, preserves independently pre-provisioned users, and emits the
  required audit events. Every successful reassignment migrates all affected Candidate-owned
  organization-scoped records, revokes all affected sessions, and preserves independently
  pre-provisioned users; every injected migration failure leaves the mapping and all affected
  records unchanged.

## Assumptions

- The PRD is the business source of truth; this specification does not infer functionality from
  the PRD's recommended architecture.
- V1 users are internal, and external candidates are out of scope as stated in the PRD.
- Candidate, Admin, and Manager are the only roles governed by this authentication feature because
  they are the three roles explicitly defined in PRD FR-1.
- Google OAuth2 is required for all three roles. First-login Candidate registration is restricted
  to Google email domains with an approved organization mapping.
- Candidate access to "own data" includes only data made available by other approved features;
  this specification governs authorization, not the contents of those features.
- Identity proofing during interview proctoring is a separate capability that consumes the
  Candidate identity association established here.
