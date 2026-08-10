# Security and Privacy Review

**Feature**: Role-based profile, JD, and interview management
**Review date**: 2026-08-10
**Disposition**: Automated/code review controls pass; human accessibility and usability release
evidence remains tracked separately.

## Data inventory and trust boundaries

| Data | Entry boundary | Persistence/exposure rule | Evidence |
|---|---|---|---|
| Google name and picture | Signed, fully validated ID token | Name and an HTTPS picture URL may be stored on the User and returned only from authenticated profile/user contracts | `app/auth/google_oidc.py`, `tests/unit/auth/test_google_oidc.py`, `tests/integration/test_google_callback.py` |
| JD title/content | Authenticated Manager request with CSRF | Stored in the Manager's organization; Manager reads are owner-scoped and Admin reads are explicitly application-wide | `app/jds/router.py`, `app/jds/service.py`, `tests/integration/test_jd_api.py` |
| Uploaded document | Bounded multipart request | At most 5 MiB is read; only normalized extracted text and a format enum are persisted. Raw bytes and original filename are not persisted, audited, logged, or returned | `app/jds/documents.py`, `app/jds/router.py`, `tests/unit/jds/test_documents.py` |
| Schedule identifiers/time | Authenticated Manager request with CSRF and UUID idempotency header | Candidate, owned JD, Manager, and tenant association are persisted atomically; the raw idempotency key is represented only by SHA-256 digest | `app/interviews/service.py`, `tests/integration/test_interview_api.py`, `tests/integration/test_schedule_idempotency.py` |
| Session and CSRF secrets | HttpOnly session cookie and double-submit CSRF | Only digests are persisted; browser-performance plaintext state is mode 0600 in a mode 0700 temporary directory and is removed by the runner trap | `app/auth/sessions.py`, `scripts/run-role-interview-performance.sh` |

## Control findings

### Authorization and tenant isolation — PASS

- Candidate endpoints derive the Candidate from the authenticated session and do not accept a
  browser-supplied Candidate ID.
- Manager JD and interview queries begin with organization and owner predicates. Scheduling locks
  and revalidates the active Manager, active Candidate, and Manager-owned JD in one transaction.
- Admin application-wide user/JD access is guarded by the backend Admin dependency. Direct
  cross-role calls receive a safe denial independently of frontend navigation.
- Tenant reassignment either migrates a safe single-owner relationship or rejects the complete
  transaction when a scheduled interview has multiple owners. Rollback tests cover injected
  participant failures.

### Upload parser and resource limits — PASS

- Extension and MIME must agree and PDF/DOCX signatures are parsed rather than trusted.
- PDF encryption, malformed input, DOCX path traversal, encrypted archives, macros, excessive
  entries, expanded size, and compression ratio are rejected. TXT is strict UTF-8 and rejects NUL.
- Empty extracted content is rejected. Parser failures map to stable safe errors and never include
  parser/provider exception text.
- The filename is reduced to a basename for parser metadata but is never stored, logged, audited,
  or returned. No raw download endpoint exists in this feature.

### Profile picture and browser security — PASS

- Picture claims are accepted only after issuer, signature, audience, expiry, nonce, email, and
  application claim validation, and only absolute HTTPS picture URLs survive validation.
- The frontend uses `referrerPolicy="no-referrer"`, supplies accessible fallback initials, and
  falls back when image loading fails. It does not expose OAuth tokens or provider errors.
- Credentialed CORS is explicit-origin only. POST/PATCH operations require the existing same-origin
  double-submit CSRF check; `Idempotency-Key` is explicitly allowlisted.

### Audit, logs, metrics, and telemetry — PASS

- Audit metadata is fail-closed against an explicit key allowlist. JD audit contains only source
  type/format; scheduling contains only replay state. It excludes email, name, title, content,
  filename, picture URL, document bytes, session/CSRF values, and raw idempotency keys.
- Google rejection logs contain bounded reason labels only. Structured logging recursively redacts
  secret-bearing keys; metric labels reject secret-bearing names and use bounded role/status/reason
  labels.
- Performance evidence contains operation/role counts and latency only. The runner copies only
  sanitized baseline/browser reports, never its session-state or service logs.

### Error and transaction behavior — PASS

- Public errors use stable codes, safe recovery text, and an opaque correlation ID. Raw database,
  parser, provider, and authorization details are not returned.
- JD creation/upload and interview scheduling use the request transaction. Invalid upload,
  inaccessible resources, idempotency mismatch, concurrent role/status loss, and injected failures
  leave no partial JD/interview/audit state.

## Residual risks and operational requirements

- PostgreSQL storage growth from extracted JD content must be monitored; this release deliberately
  has no raw-file retention or download lifecycle.
- Google picture URLs cause the user's browser to contact Google when a valid image is displayed.
  The no-referrer policy limits request context, and the accessible local fallback remains usable.
- Performance evidence files are local release artifacts and may reveal timing/environment version
  information. They must not be served by the application.
- Production database recovery uses a new forward corrective migration and a verified backup;
  feature-destructive downgrade is limited to the exact guarded disposable test database.

No unresolved high- or critical-severity security/privacy finding was identified in this review.
