# Feature Specification: Role-Based Interview Management

**Feature Branch**: `001-user-auth`

**Created**: 2026-08-09

**Status**: Draft

**Input**: Authentication, role-based home screens, profile access, JD management, and candidate interview scheduling for Candidate, Manager, and Admin users.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Authenticate and Reach the Correct Home Screen (Priority: P1)

An approved Candidate, Manager, or Admin signs in with Google OAuth and is taken directly to the home
screen for their assigned role. The user can later log out, which ends the authenticated session
and returns them to the login page.

**Why this priority**: Authentication and correct role routing are prerequisites for every other
journey and protect each role's information and actions.

**Independent Test**: Sign in once as each supported role, verify the destination and available
functionality, then log out and confirm that the former session can no longer access a protected
page.

**Acceptance Scenarios**:

1. **Given** an unauthenticated visitor, **When** the visitor opens the application, **Then** the login page displays a Google sign-in control.
2. **Given** an approved Candidate, **When** Google authentication succeeds, **Then** the Candidate home screen is displayed.
3. **Given** an approved Manager, **When** Google authentication succeeds, **Then** the Manager home screen is displayed.
4. **Given** an approved Admin, **When** Google authentication succeeds, **Then** the Admin home screen is displayed.
5. **Given** a signed-in user, **When** the user logs out, **Then** the session is terminated, the login page is displayed, and protected pages require a new sign-in.
6. **Given** a user assigned one supported role, **When** the user requests a page or action reserved for another role, **Then** access is denied even if the request does not originate from visible navigation.

---

### User Story 2 - Manage and Use a Personal Profile (Priority: P2)

After login, every user can identify their signed-in account from a profile picture in the
application header. The profile menu provides Profile and Logout actions. The dedicated profile
page shows the user's profile picture, name, and email.

**Why this priority**: A consistent account experience helps users confirm which identity is active
and provides a predictable route to profile information and logout.

**Independent Test**: Sign in as any supported role, open the profile menu, visit the profile page,
verify the displayed identity, and use the menu to log out.

**Acceptance Scenarios**:

1. **Given** a signed-in user, **When** any authenticated page is displayed, **Then** the user's profile picture appears in the top-right corner.
2. **Given** a signed-in user, **When** the profile picture is activated, **Then** a menu containing Profile and Logout is displayed.
3. **Given** the profile menu is open, **When** Profile is selected, **Then** a dedicated profile page shows the authenticated user's profile picture, name, and email.
4. **Given** the profile menu is open, **When** Logout is selected, **Then** the session is terminated and the login page is displayed.
5. **Given** a user attempts to request another user's profile, **When** access is evaluated, **Then** the user receives no other user's profile information through the personal profile experience.

---

### User Story 3 - Candidate Views Allocated Interviews (Priority: P2)

A Candidate sees a home-screen list containing only interviews allocated to that Candidate. Each
entry identifies the interview with its JD name or title, scheduled date, scheduled time, and
current status.

**Why this priority**: Candidates need a private, dependable view of the interviews they are
expected to attend.

**Independent Test**: Allocate different interviews to two Candidates, sign in as each Candidate,
and confirm each sees only their own entries with all required identifying information.

**Acceptance Scenarios**:

1. **Given** a Candidate with one or more allocated interviews, **When** the Candidate opens the home screen, **Then** every allocated interview displays its JD name or title, date, time, and status.
2. **Given** a Candidate with no allocated interviews, **When** the Candidate opens the home screen, **Then** an empty state is shown without exposing another Candidate's interviews.
3. **Given** interviews allocated to multiple Candidates, **When** one Candidate views or directly requests interview data, **Then** only interviews allocated to that authenticated Candidate are returned.

---

### User Story 4 - Manager Creates and Reviews JDs (Priority: P2)

A Manager sees the JDs they created and can add a new JD either by entering it manually or by
uploading a JD document. The resulting JD remains available for that Manager's later scheduling
work.

**Why this priority**: JDs are required inputs for interview scheduling, and Manager ownership
keeps each Manager's working records appropriately scoped.

**Independent Test**: Sign in as a Manager, create one manual JD and upload one JD document, then
verify both appear for that Manager and do not appear in another Manager's list.

**Acceptance Scenarios**:

1. **Given** a signed-in Manager, **When** the Manager opens the home screen, **Then** the list contains only JDs created by that Manager.
2. **Given** a signed-in Manager, **When** the Manager supplies the required JD title and manual content, **Then** the JD is saved and appears in that Manager's list.
3. **Given** a signed-in Manager, **When** the Manager supplies a JD title and uploads a supported JD document, **Then** the JD is saved and appears in that Manager's list.
4. **Given** a JD created by one Manager, **When** another Manager requests that JD or the Manager JD list, **Then** the JD is not disclosed unless a later requirement explicitly grants broader access.
5. **Given** missing or unusable JD input, **When** a Manager attempts to create or upload the JD, **Then** no incomplete JD is added and the Manager receives an actionable correction message.

---

### User Story 5 - Manager Schedules Candidate Interviews (Priority: P2)

A Manager chooses a Candidate, one of the Manager's available JDs, a date, and a time to schedule
an interview. The Manager can view interviews they scheduled, and the new interview appears in the
selected Candidate's allocated-interview list.

**Why this priority**: Scheduling connects Manager-created JDs to Candidate work and produces the
core allocation the Candidate home screen must communicate.

**Independent Test**: As a Manager, select a Candidate and an existing owned JD, schedule an
interview, verify it in the Manager's scheduled list, then sign in as the selected Candidate and
verify the same allocation appears only there.

**Acceptance Scenarios**:

1. **Given** a Manager has at least one available JD and at least one Candidate is available for scheduling, **When** the Manager selects a Candidate, JD, future date, and time and confirms, **Then** one scheduled interview is created with those associations and a current status.
2. **Given** a newly scheduled interview, **When** the scheduling Manager views scheduled interviews, **Then** that interview is included with the selected Candidate, JD, date, time, and status.
3. **Given** a newly scheduled interview, **When** the selected Candidate views allocated interviews, **Then** the interview appears with the JD title, date, time, and status.
4. **Given** a newly scheduled interview for one Candidate, **When** another Candidate views or requests allocated interviews, **Then** the interview is not disclosed.
5. **Given** the Manager omits the Candidate, JD, date, or time, selects a JD not available to that Manager, or supplies a date and time that has already passed, **When** scheduling is confirmed, **Then** no interview is created and the Manager receives an actionable correction message.

---

### User Story 6 - Admin Reviews Users and JDs (Priority: P2)

An Admin sees all application users in a paginated table, can open a selected user's details in a
popup, and can change that user's role to another supported role. The Admin also sees all JDs in a
separately paginated table.

**Why this priority**: Administrators need an application-wide operational view and the ability to
maintain correct role assignments.

**Independent Test**: Sign in as an Admin, navigate multiple pages of users and JDs, open a user
detail popup, and change the selected user's role. Confirm non-Admins cannot perform the same
operations.

**Acceptance Scenarios**:

1. **Given** enough users to span multiple pages, **When** an Admin opens and navigates the user table, **Then** each page shows the appropriate subset with Name, Email, Role, and Status, and records are not duplicated or skipped between pages.
2. **Given** a visible user row, **When** the Admin selects it, **Then** a popup displays all available details for that user, including at minimum Name, Email, Role, and Status.
3. **Given** a selected user, **When** the Admin changes the role to Candidate, Manager, or Admin, **Then** the new role is saved and governs the user's subsequent authorized access and home-screen routing.
4. **Given** enough JDs to span multiple pages, **When** an Admin opens and navigates the JD table, **Then** each page shows the appropriate subset of all application JDs and records are not duplicated or skipped between pages.
5. **Given** a Candidate or Manager, **When** that user requests Admin user-management or application-wide JD data, **Then** access is denied.

### Edge Cases

- Google authentication is cancelled, rejected, or temporarily unavailable; the visitor remains
  signed out and receives a safe recovery path back to login.
- An authenticated account is disabled or its role changes between requests; subsequent access is
  evaluated against the current account state and role.
- The identity provider does not supply a usable profile image; an identifiable, accessible
  placeholder is shown while name and email remain available.
- A Candidate or Manager has no interviews or JDs; the correct empty state is shown without data
  from another user.
- A paginated Admin result set changes while the Admin moves between pages; each response remains
  authorized and does not expose records outside the requested page.
- A JD upload is empty, unreadable, or not a supported document; the record is not created and the
  Manager is told how to correct the submission.
- A Candidate, JD, or Manager account becomes unavailable before scheduling is confirmed; no
  partial interview allocation is created.
- A scheduling request is repeated accidentally; the user receives a single clear outcome and can
  distinguish any interviews that were actually created.
- A user tries to reach another role's page or retrieve another owner's data through a saved link
  or direct request; access is denied without disclosing protected data.

## Requirements *(mandatory)*

### Functional Requirements

#### Authentication and common profile experience

- **FR-001**: The system MUST provide a login page with a Google sign-in control and MUST use Google OAuth authentication for Candidate, Manager, and Admin users.
- **FR-002**: The system MUST allow only approved users to establish an authenticated application session after successful Google OAuth authentication.
- **FR-003**: The system MUST redirect an authenticated user to the Candidate, Manager, or Admin home screen according to the user's current assigned role.
- **FR-004**: The system MUST terminate the authenticated session when the user logs out and MUST return the user to the login page.
- **FR-005**: Every authenticated screen MUST display the current user's profile picture in the top-right application area.
- **FR-006**: Activating the profile picture MUST open a menu containing Profile and Logout actions.
- **FR-007**: Selecting Profile MUST navigate to a dedicated page that displays the authenticated user's profile picture, name, and email.
- **FR-008**: Selecting Logout from the profile menu MUST produce the logout behavior defined in FR-004.

#### Candidate experience

- **FR-009**: The Candidate home screen MUST show only interviews allocated to the authenticated Candidate.
- **FR-010**: Each Candidate interview entry MUST display the associated JD name or title, scheduled date, scheduled time, and current interview status.
- **FR-011**: A Candidate MUST NOT view another Candidate's allocated interviews through either the visible interface or a direct data request.

#### JD management and Manager experience

- **FR-012**: The system MUST persist each JD record so it remains available for later viewing and interview scheduling.
- **FR-013**: A JD MUST contain a name or title and the JD content supplied manually or through an uploaded document, and MUST retain its creating Manager association.
- **FR-014**: The Manager home screen MUST list only JDs created by the authenticated Manager.
- **FR-015**: A Manager MUST be able to create a JD by supplying its required information manually.
- **FR-016**: A Manager MUST be able to create a JD by uploading a PDF, DOCX, or plain-text JD document and supplying the JD name or title.
- **FR-017**: A Manager MUST NOT view or use a JD created by another Manager unless a later approved requirement explicitly grants broader access.
- **FR-018**: The system MUST reject missing, empty, unreadable, or unsupported JD submissions without creating an incomplete JD and MUST tell the Manager how to correct the input.

#### Interview scheduling

- **FR-019**: The system MUST persist each scheduled interview and associate it with exactly one Candidate, one JD, the scheduling Manager, a scheduled date, a scheduled time, and an interview status.
- **FR-020**: A Manager MUST be able to initiate scheduling and choose a Candidate, one JD available to that Manager, a date, and a time.
- **FR-021**: The system MUST reject a scheduling attempt when any required selection is absent, the selected JD is unavailable to the Manager, or the selected date and time are in the past.
- **FR-022**: After successful scheduling, the interview MUST appear in the selected Candidate's allocated-interview list.
- **FR-023**: A Manager MUST be able to view only interviews scheduled by that Manager, including the associated Candidate, JD, date, time, and status.
- **FR-024**: Scheduling MUST complete as one outcome: either the interview and Candidate allocation are both available, or neither is created.

#### Admin experience and authorization

- **FR-025**: The Admin home screen MUST display all application users in a server-paginated table containing Name, Email, Role, and Status.
- **FR-026**: Selecting a user row MUST open a detail popup showing all details available to the Admin for that user, including at minimum Name, Email, Role, and Status.
- **FR-027**: An Admin MUST be able to change a selected user's role to Candidate, Manager, or Admin.
- **FR-028**: The Admin home screen MUST display all application JDs in a server-paginated table.
- **FR-029**: Server pagination MUST allow the Admin to move through complete user and JD result sets without duplicate or skipped records in a stable, unchanged result set.
- **FR-030**: The system MUST enforce all role and ownership restrictions for protected pages, operations, and returned data independently of frontend navigation or visibility.
- **FR-031**: Candidate access MUST be limited to Candidate functionality, the authenticated Candidate's profile, and that Candidate's allocated interviews.
- **FR-032**: Manager access MUST include personal profile, owned-JD creation and upload, Candidate interview scheduling with owned JDs, and interviews scheduled by that Manager, but MUST exclude Admin user management and other Managers' owned data.
- **FR-033**: Admin access MUST include personal profile, application-wide user viewing, user detail inspection, supported-role changes, and application-wide JD viewing.
- **FR-034**: Unauthorized requests MUST be denied without returning protected user, JD, or interview information.

### Key Entities

- **User**: An approved person who authenticates with Google; has a profile picture, name, email,
  current role (Candidate, Manager, or Admin), and status.
- **User Profile**: The authenticated user's personal view of profile picture, name, and email.
- **Job Description (JD)**: A persistent interview subject identified by a name or title, containing
  manually supplied or uploaded JD content, and associated with the Manager who created it.
- **Scheduled Interview**: A persistent allocation associating one Candidate with one JD, the
  Manager who scheduled it, its scheduled date and time, and its current status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In role-routing verification, 100% of approved Candidate, Manager, and Admin accounts reach the correct home screen after successful sign-in.
- **SC-002**: In authorization verification, 100% of attempts to access another role's restricted functionality or another user's owned interviews or JDs are denied without protected-data disclosure.
- **SC-003**: At least 95% of users can sign in, reach their role home, open their profile, and log out successfully on the first attempt without assistance.
- **SC-004**: At least 95% of authenticated page views present the user's profile menu and requested home-screen information within 2 seconds under normal business load.
- **SC-005**: A Manager can complete manual JD creation or a valid JD upload in under 3 minutes, and the new JD appears in the Manager's list immediately after success.
- **SC-006**: A Manager can schedule an interview using an existing JD in under 2 minutes once the Candidate, JD, date, and time are known.
- **SC-007**: In 100% of successful scheduling verification cases, exactly one interview appears for both the scheduling Manager and the selected Candidate, and appears for no other Candidate.
- **SC-008**: An Admin can locate a user through paginated navigation, open the user's details, and change the role in under 2 minutes for result sets of at least 1,000 users.
- **SC-009**: Admin user and JD pagination exposes every record exactly once across an unchanged result set of at least 1,000 records, with no missing or duplicate rows.
- **SC-010**: At least 90% of Candidate, Manager, and Admin participants complete their primary home-screen task without assistance in acceptance testing.
- **SC-011**: All login, profile, home-screen, table, popup, JD, scheduling, and logout journeys meet WCAG 2.2 AA and can be completed using only a keyboard and a screen reader.

## Assumptions

- The existing approved-user and approved-domain rules determine who may establish an account or
  session; this feature does not add a separate public registration form.
- Each user has exactly one current role from Candidate, Manager, or Admin for this feature.
- Google is the source of the profile picture, name, and email shown by the common profile
  experience; an accessible placeholder is used when no usable picture is available.
- PDF, DOCX, and plain-text are the supported JD document formats described by the source PRD.
- A newly created interview receives the application's normal initial scheduled status; Managers
  do not choose a status while scheduling.
- Dates and times use the application's consistent business-time convention and clearly communicate
  the scheduled moment to both Manager and Candidate.
- Candidate selection exposes only the candidate information needed to identify the scheduling
  choice; broader Candidate profile access is outside this feature.
- User profile editing, JD editing/deletion, interview rescheduling/cancellation, notifications,
  candidate self-scheduling, interview execution, JD skill extraction, scoring, reports, and
  profile resume or skill-matrix management are outside this feature.
- The Admin's JD capability in this feature is view-only; Manager JD access remains ownership
  scoped. No broader role permissions are implied.
- Result sets are expected to support at least 1,000 users and 1,000 JDs for measurable pagination
  acceptance testing.
