# Usability and Workflow Timing Protocol

**Feature**: Role-based profile, JD, and interview management
**Protocol prepared**: 2026-08-10
**Release status**: BLOCKED — no human participant runs have been supplied or observed.

## Recruitment and privacy

Recruit at least 20 representative internal participants, including at least five participants for
each of Candidate, Manager, and Admin. A participant may execute more than one role, but each role
must still have five distinct participants. Use seeded non-production accounts and realistic but
non-confidential JDs. Explain the task goal without naming the controls or navigation path.

Record only an anonymized participant code, assigned role, task code, first-attempt result, whether
help was requested/given, and elapsed seconds. Do not record names, emails, OAuth/session values,
uploaded filenames/content, or free-form observations containing personal information.

## Task and timing definitions

| Code | Task | Start | Stop | Threshold |
|---|---|---|---|---|
| AUTH | Login, reach role home, view Profile, logout | Login page visible | Login page visible after logout | At least 90% first-attempt success |
| CAND | Identify one allocated interview | Candidate home ready | Correct JD/date/time/status identified | Primary-task criteria below |
| JD-M | Create a manual JD | Manager home ready | Created JD visibly confirmed in owned list | Under 180 seconds |
| JD-U | Upload a valid JD | Manager home ready | Uploaded JD visibly confirmed in owned list | Under 180 seconds |
| SCHED | Schedule one Candidate using an owned JD | All four choices visible | Interview visibly confirmed in Manager list | At least 90% under 120 seconds |
| ADMIN | Find/inspect a user and JD, then change role | Admin tables ready | Updated role visibly confirmed after detail open | At least 90% under 120 seconds |

Every Manager sample must include both JD-M and JD-U; the two paths are measured and reported
separately. A primary role task is: Candidate identifies an allocation; Manager completes JD-M or
JD-U and SCHED; Admin locates/inspects one user and one JD.

## Observation sheet

| Participant | Role | Task | First attempt | Help requested | Help given | Seconds |
|---|---|---|---|---|---|---:|
| Pending | Pending | Pending | Pending | Pending | Pending | Pending |

## Calculations and blocking thresholds

Report numerator/denominator and percentage for each outcome; do not combine manual and upload JD
samples. Release requires:

- AUTH: at least 18 of 20 first-attempt successes.
- Primary home task: at least 18 of 20 complete without assistance.
- JD-M: every recorded valid run under 180 seconds, with at least five Manager runs.
- JD-U: every recorded valid run under 180 seconds, with at least five Manager runs.
- SCHED: at least 90% of Manager runs under 120 seconds.
- ADMIN: at least 90% of Admin runs under 120 seconds.
- Any participant-visible defect is triaged; a material defect is fixed and the affected task is
  rerun before sign-off.

## Results

No participant sessions were run by the coding agent. T097, SC-003, SC-005, SC-006, SC-008, and
SC-010 remain incomplete until authorized human evidence populates the observation sheet and the
calculations meet every threshold.
