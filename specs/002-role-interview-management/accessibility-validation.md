# Accessibility Validation

**Feature**: Role-based profile, JD, and interview management
**Automated validation date**: 2026-08-10
**Release status**: BLOCKED — a human NVDA or VoiceOver session is still required.

## Automated and keyboard evidence

The production-build Playwright suites cover:

- Candidate, Manager, and Admin focused page headings and direct role-home navigation.
- Skip-link and profile-disclosure keyboard operation, Escape close, and focus return.
- Candidate allocation semantics, Manager manual/upload/scheduling forms, Admin tables, independent
  pagination landmarks, and Admin detail-dialog focus restoration.
- Loading, empty, populated, success, and safe error/live-region states.
- Axe scans for every role home, an open profile disclosure, an invalid upload state, and an open
  Admin dialog. Eight integrated management/accessibility journeys passed with no reported axe
  violations.
- A 320 × 720 Manager viewport with an upload validation error. It has no document-level horizontal
  overflow; file input and responsive grid content shrink within the viewport.
- Visible focus outlines, non-color status/error text, 44-pixel interactive targets, labeled
  scrollable tables, reduced-motion overrides, and high-contrast foreground/background tokens in
  `apps/web/src/styles.css`.

Component tests exhaust disclosure outside-click/Escape cleanup, image-error fallback, page-heading
focus, dialog cancellation/close/focus return, form errors/success, and pagination boundaries.
Frontend unit coverage is an exact 100% for lines, branches, functions, and statements.

## Manual screen-reader protocol — pending

Run on the production build with either NVDA + current Firefox/Chrome on Windows or VoiceOver +
current Safari on macOS. Record tool/browser versions and anonymized tester code. Do not record user
email, JD content, filenames, or session values.

For each supported role, verify without a pointer:

1. The page title and focused H1 announce once after login/navigation.
2. Skip to main content moves focus past repeated header navigation.
3. Role navigation exposes the current destination and no inaccessible-role links.
4. The profile trigger announces its name and expanded/collapsed state; Profile and Logout are
   ordinary link/button controls; Escape closes and returns focus.
5. Profile image or placeholder has appropriate useful/decorative text.
6. Tables announce caption, column headers, row/cell relationships, and textual status.
7. Manager form labels, required state, file format guidance, validation errors, busy state, and
   success announcements are understandable in browse and forms modes.
8. Admin dialog announces title/modality, keeps navigation within the dialog, supports Escape, and
   returns focus to the originating row control.
9. Loading, error, retry, success, and session-expiry announcements are timely and not duplicated.
10. At 200% and 400% zoom/reflow, controls remain reachable without two-dimensional page scrolling.

## Manual evidence record

| Tester | Screen reader/browser | Roles | Findings | Retest | Result |
|---|---|---|---|---|---|
| Pending | Pending | Pending | Pending | Pending | Not run |

T096 and SC-011 cannot be signed off until the pending human screen-reader row is replaced with
real evidence and every material finding is resolved and retested.
