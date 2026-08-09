# Authentication Security and Privacy Review

Reviewer: Codex implementation security review

Date: 2026-08-09

Outcome: no unresolved critical or high-severity finding. Release remains conditional on the
manual screen-reader check and staging Google smoke test, which are not security defects.

| Area | Decision/evidence | Result |
|---|---|---|
| OIDC validation | backend verifies signature, issuer, audience, expiry, nonce, verified email | Pass |
| OAuth CSRF/replay | hashed one-time state, nonce, PKCE S256, expiry, row lock, allowlisted return paths | Pass |
| PKCE key rotation | Fernet current/previous key IDs; ciphertext only; missing key fails closed | Pass |
| Cookies/session fixation | new opaque token after callback; SHA-256 digest at rest; Host/Secure/HttpOnly/SameSite production policy | Pass |
| CSRF/CORS | exact Origin allowlist, double-submit token bound to session digest, credentialed explicit CORS | Pass |
| Global revocation | role/disable/logout revoke every live row; generation checked on every request | Pass |
| Identity collision/enumeration | first verified normalized-email binding only; later subject-only; safe uniform public errors | Pass |
| Domain spoofing/IDNA | provider email is syntactically validated; domains use lower-case IDNA ASCII and exact equality; wildcards, URLs, `@`, trailing dots, malformed labels, and implicit subdomains are rejected | Pass |
| Registration provenance | nullable immutable mapping FK distinguishes self-registered Candidates from independent pre-provisioning; removed mapping incarnations remain soft-retired | Pass |
| Mapping concurrency | create/register/remove/reassign share a transaction advisory lock, then deterministic row locks; independent-session race tests prove complete before/after states | Pass |
| Tenant reassignment | target email collisions preflight; auth-owned rows cascade; typed participants share one AsyncSession and any failure rolls back the entire transaction | Pass |
| Authorization/tenancy | deny-default capability plus organization/owner/allocating/managing scopes | Pass |
| Candidate invariant | DB uniqueness/same-org FK plus transactional role/profile service invariant | Pass |
| Redirects/provider tokens | fixed relative return allowlist is joined only to validated `FRONTEND_APPLICATION_ORIGIN`; Host/Forwarded headers and provider credentials never control browser destinations | Pass |
| Cache/history | `no-store`, clear browser cache on logout, protected state cleared across tabs | Pass |
| Audit privacy/secrets | metadata key allowlist excludes domain/email/name/token values; historical organization rows remain immutable; safe transition IDs and counts are correlated | Pass |
| Fake provider isolation | production settings reject fake provider and insecure redirect/cookie/origin policy | Pass |
| Trusted proxies | application does not use forwarded identity/security headers; deployment must restrict Uvicorn forwarded IPs | Pass |
| Rate limiting | deployment gateway login/callback throttling is required; application returns non-enumerating errors | Accepted medium operational risk; Platform owner; due before public exposure |

Operational follow-up: staging must verify gateway throttling and trusted-proxy allowlists before
public exposure. This does not change the v1 functional contract and is tracked as a deployment
control rather than an unresolved high-severity application defect.
