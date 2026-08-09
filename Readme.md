# MockInterview

MockInterview is an AI-assisted technical interview simulation platform for running consistent,
auditable mock interviews at scale. It is intended to help teams turn a client job description or
an internal skill benchmark into a targeted interview, evidence-backed scoring, and a readiness
report without requiring a human interviewer for the entire session.

The repository currently contains the authentication and authorization foundation. The broader
product vision includes JD ingestion, candidate profiles, adaptive voice/video interviews, a shared
code editor, proctoring, scoring, mentor review, and readiness reporting. See the
[product requirements](docs/MockInterview_PRD.md) for that roadmap; those modules should not be
assumed to be implemented yet.

## Current capabilities

- Google OIDC login only; there are no passwords or public registration forms.
- Admin pre-provisioning plus controlled first-login Candidate registration for exact approved
  Google email-domain mappings.
- Admin-only domain mapping list/create/reassign/remove APIs with immutable registration
  provenance, atomic Candidate tenant migration, and session revocation.
- Candidate, Manager, and Admin role-based access with organization and ownership checks.
- Admin user provisioning, role changes, and enable/disable operations.
- Server-side PostgreSQL sessions with an 8-hour absolute and 2-hour idle lifetime.
- Global session revocation on logout, role change, or account disablement.
- Security-conscious OAuth state, nonce, PKCE, CSRF, cookie, audit, and metrics handling.
- Accessible React role landing pages and authentication recovery states.

Role intent:

| Role | Product access |
| --- | --- |
| Candidate | Assigned interviews and permitted candidate-owned data only |
| Manager | JD upload, interview allocation, and readiness for interviews they manage |
| Admin | User administration and application-wide operational access |

## Technology

- Web: React 19, Vite 7, strict TypeScript
- API: Python 3.12, FastAPI, SQLAlchemy, Alembic, Authlib
- Database and session store: PostgreSQL 17
- Tests: Pytest, Vitest, Playwright, and axe-core

The main source directories are `apps/web` and `apps/api`. Feature specifications and contracts are
under `specs/001-user-auth`.

## Prerequisites

- Docker with Docker Compose
- Python 3.12
- Node.js 22–24 and npm
- A Google Cloud OAuth 2.0 Web application for real sign-in

Create a Google OAuth client and register the exact callback used in your environment. For direct
API development, the callback is:

```text
http://localhost:8000/api/v1/auth/google/callback
```

Do not commit the client secret, database password, cookies, authorization codes, or Fernet keys.

## Run locally

### 1. Configure the environment

```bash
cp .env.example .env.local
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install --requirement apps/api/requirements.lock
.venv/bin/python -m pip install --no-deps --editable apps/api
npm ci --prefix apps/web
```

Generate a Fernet key:

```bash
.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

Edit `.env.local` and replace every placeholder. For PostgreSQL started by Compose, use:

```dotenv
DATABASE_URL=postgresql+psycopg://mockinterview:local-development-only@localhost:5432/mockinterview
OAUTH_TRANSACTION_ENCRYPTION_KEYS=current=<generated-fernet-key>
```

Also set the Google client ID and secret. Keep `ENABLE_FAKE_OIDC=false`; the deterministic provider
is reserved for automated tests.

### 2. Start PostgreSQL, migrate, and seed users

```bash
docker compose up -d postgres
.venv/bin/python -m alembic -c apps/api/alembic.ini upgrade head
.venv/bin/python apps/api/scripts/seed_auth.py \
  --env-file .env.local \
  --user CANDIDATE:candidate@example.com:"Local Candidate" \
  --user MANAGER:manager@example.com:"Local Manager" \
  --user ADMIN:admin@example.com:"Local Admin"
```

Use Google-account email addresses you control if you want to exercise real sign-in. Seeding is
idempotent and does not store Google subjects; the verified subject is bound atomically on first
login.

### 3. Start the API and web application

In one terminal, load `.env.local` through Uvicorn and run the API:

```bash
.venv/bin/python -m uvicorn app.main:build_app \
  --factory --app-dir apps/api --env-file .env.local \
  --host 0.0.0.0 --port 8000 --reload
```

In another terminal, run the web application:

```bash
npm --prefix apps/web run dev
```

- API health: `http://localhost:8000/health`
- API documentation: `http://localhost:8000/docs`
- Vite development server: `http://localhost:5173`

The browser application deliberately calls `/api/v1` on the same origin so authentication cookies
remain host-only. A full browser login therefore requires a local reverse proxy that exposes one
origin and routes requests as follows:

| Request path | Local target |
| --- | --- |
| `/api/v1/*` and `/health` | `http://localhost:8000` |
| All other paths | `http://localhost:5173` |

When using a proxy such as `http://localhost:8080`, update `GOOGLE_OIDC_REDIRECT_URI`,
`FRONTEND_ORIGINS`, and `CSRF_ALLOWED_ORIGINS` to that origin and register the matching Google
callback. The API and UI can still be developed independently on ports 8000 and 5173.

### Docker Compose alternative

After creating `.env.local`, all three development services can be started with:

```bash
docker compose up
```

For the API container, change the database host in `.env.local` from `localhost:5432` to
`postgres:5432`. Compose starts PostgreSQL, the API, and Vite, but the same-origin reverse-proxy
requirement above still applies to an end-to-end browser login.

Stop the services with:

```bash
docker compose down
```

Add `--volumes` only when you intentionally want to delete local PostgreSQL and Node volume data.

## Production deployment

Production should use three independently deployable components behind one HTTPS origin:

1. Serve the built web assets from a CDN or web server.
2. Route `/api/v1/*` and `/health` to the FastAPI service.
3. Connect the API to a managed PostgreSQL 17 database with TLS, backups, and restricted network
   access.

Build the web application:

```bash
npm ci --prefix apps/web
npm --prefix apps/web run build
```

The deployable static output is `apps/web/dist`.

Install and start the API in a Python 3.12 image or runtime:

```bash
python -m pip install --requirement apps/api/requirements.lock
python -m pip install --no-deps --editable apps/api
python -m uvicorn app.main:build_app \
  --factory --app-dir apps/api --host 0.0.0.0 --port 8000
```

The checked-in Alembic URL is intentionally local-development-only. Run this environment-aware
migration command as a single release job before rolling out production API instances:

```bash
python -c 'import os; from alembic import command; from alembic.config import Config; config = Config("apps/api/alembic.ini"); config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"]); command.upgrade(config, "head")'
```

Use forward migrations for production recovery rather than downgrading a live database.

Set production configuration through a secret manager or deployment environment. Required security
settings include:

```dotenv
APP_ENV=production
DATABASE_URL=postgresql+psycopg://<user>:<password>@<database-host>:5432/<database>
GOOGLE_OIDC_REDIRECT_URI=https://<application-host>/api/v1/auth/google/callback
SESSION_ABSOLUTE_SECONDS=28800
SESSION_IDLE_SECONDS=7200
SESSION_COOKIE_NAME=__Host-mi_session
SESSION_COOKIE_SECURE=true
FRONTEND_ORIGINS=["https://<application-host>"]
CSRF_ALLOWED_ORIGINS=["https://<application-host>"]
FRONTEND_APPLICATION_ORIGIN=https://<application-host>
ENABLE_FAKE_OIDC=false
```

Also supply the Google issuer, client credentials, OAuth return-path allowlist, and one or more
Fernet keys from `.env.example`. Put a newly rotated key first and retain the previous key for at
least the configured OAuth transaction lifetime. Application startup fails closed when production
cookie, HTTPS, origin, provider, database, or session settings are unsafe.

Before directing traffic, verify `/health`, sign-in and callback behavior, global logout from two
sessions, Admin role/status revocation, and the audit trail. Do not use the development Compose
credentials in any deployed environment.

## API overview

| Method and path | Purpose |
| --- | --- |
| `GET /api/v1/auth/google/login` | Start Google OIDC login |
| `GET /api/v1/auth/google/callback` | Validate the provider response and create a session |
| `GET /api/v1/auth/me` | Return the current minimal user identity and role |
| `POST /api/v1/auth/logout` | Revoke all sessions for the current user |
| `POST /api/v1/admin/users` | Pre-provision a user |
| `PATCH /api/v1/admin/users/{id}/role` | Change a role and revoke existing sessions |
| `PATCH /api/v1/admin/users/{id}/status` | Enable or disable a user and revoke sessions |
| `GET /api/v1/admin/organization-domain-mappings` | List active approved domains |
| `POST /api/v1/admin/organization-domain-mappings` | Create an approved domain mapping |
| `PATCH /api/v1/admin/organization-domain-mappings/{id}` | Atomically reassign mapped Candidates |
| `DELETE /api/v1/admin/organization-domain-mappings/{id}` | Soft-remove and disable mapped Candidates |

The generated OpenAPI documentation is the source of truth for request and response schemas.

## Validation

Install Playwright's Chromium browser once:

```bash
npx playwright install chromium
```

Run the complete blocking quality gate:

```bash
MOCKINTERVIEW_PYTHON=.venv/bin/python bash scripts/quality-gate.sh
```

The gate runs dependency-license checks, Ruff, MyPy, backend tests, ESLint, TypeScript checks,
frontend tests, and Playwright end-to-end tests. The required coverage threshold is 100% for lines,
branches, functions, and statements, as defined in `.coverage-thresholds.json`.

## Operations and documentation

- [Authentication operations](docs/authentication.md)
- [User-auth specification](specs/001-user-auth/spec.md)
- [Local validation scenarios](specs/001-user-auth/quickstart.md)
- [Product requirements](docs/MockInterview_PRD.md)

Expired OAuth transaction state can be cleaned with:

```bash
.venv/bin/python apps/api/scripts/cleanup_auth_state.py
```

For a suspected session compromise, disable the affected user or perform a security revocation,
confirm that all active sessions are revoked, and inspect correlated audit events. Never place raw
OIDC claims, Google subjects, emails, cookies, state, nonce, or authorization codes in logs or
incident tickets.
