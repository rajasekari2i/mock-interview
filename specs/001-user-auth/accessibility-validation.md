# WCAG 2.2 AA Validation

Date: 2026-08-09

Automated Playwright/axe coverage includes login, safe error, Candidate, Manager, Admin, protected
state, and expired-session views. Component tests cover alert/status roles, role-aware navigation,
Google-only controls, and deterministic heading focus.

## Manual keyboard checklist

- [x] Tab order follows document order and reaches the Google/recovery and role navigation links.
- [x] Enter activates every link and Space/Enter activates the logout button.
- [x] Focus moves to the page heading after authentication, error, role, and expiry transitions.
- [x] No keyboard trap is present; browser back/forward does not disclose authenticated API data.
- [x] Errors use `role=alert`; loading uses `role=status`; meaning does not depend on color.
- [x] Default and focus contrast is validated by axe in Chromium.

## Screen-reader checklist

- [ ] Run NVDA with current Firefox or VoiceOver with current Safari and record tester/version.
- [ ] Confirm login heading and Google link names are announced once and in order.
- [ ] Confirm safe errors and session-ending messages are announced immediately without secrets.
- [ ] Confirm each role navigation landmark and current page heading has an unambiguous name.

The execution environment has neither NVDA nor VoiceOver. These four checks remain a release
prerequisite requiring a human tester on Windows or macOS; they are not represented as passed by
browser accessibility-tree automation.
