#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${project_root}"

required_database="mockinterview_role_interview_performance"
performance_database_url="${PERFORMANCE_DATABASE_URL:-}"
if [[ -z "${performance_database_url}" ]]; then
  echo "PERFORMANCE_DATABASE_URL is required" >&2
  exit 2
fi

mapfile -t parsed_urls < <(.venv/bin/python - "${performance_database_url}" <<'PY'
import sys
from urllib.parse import urlsplit, urlunsplit

value = sys.argv[1]
parsed = urlsplit(value)
if parsed.scheme not in {"postgresql+psycopg", "postgresql+psycopg_async"}:
    raise SystemExit("Performance URL must use the PostgreSQL psycopg driver")
database = parsed.path.removeprefix("/")
if database != "mockinterview_role_interview_performance":
    raise SystemExit("Refusing database other than mockinterview_role_interview_performance")
maintenance = urlunsplit((parsed.scheme, parsed.netloc, "/postgres", parsed.query, ""))
psql_maintenance = urlunsplit(("postgresql", parsed.netloc, "/postgres", parsed.query, ""))
print(database)
print(maintenance)
print(psql_maintenance)
PY
)
if [[ "${parsed_urls[0]:-}" != "${required_database}" ]]; then
  echo "Exact performance database guard failed" >&2
  exit 2
fi
maintenance_database_url="${parsed_urls[1]}"
psql_maintenance_url="${parsed_urls[2]}"

state_dir="$(mktemp -d "${TMPDIR:-/tmp}/mockinterview-role-performance.XXXXXX")"
chmod 700 "${state_dir}"
api_pid=""
preview_pid=""
database_created=0

cleanup() {
  local exit_status=$?
  trap - EXIT INT TERM
  if [[ -n "${preview_pid}" ]]; then kill "${preview_pid}" 2>/dev/null || true; fi
  if [[ -n "${api_pid}" ]]; then kill "${api_pid}" 2>/dev/null || true; fi
  if [[ -n "${preview_pid}" ]]; then wait "${preview_pid}" 2>/dev/null || true; fi
  if [[ -n "${api_pid}" ]]; then wait "${api_pid}" 2>/dev/null || true; fi
  if [[ "${database_created}" -eq 1 ]]; then
    psql "${psql_maintenance_url}" -v ON_ERROR_STOP=1 \
      -c "DROP DATABASE IF EXISTS ${required_database} WITH (FORCE)" >/dev/null || true
  fi
  rm -rf -- "${state_dir}"
  exit "${exit_status}"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if ! npx --prefix apps/web playwright install --with-deps chromium; then
  echo "System dependency installation was unavailable; verifying the existing dependencies with a user-level Chromium install." >&2
  npx --prefix apps/web playwright install chromium
fi

psql "${psql_maintenance_url}" -v ON_ERROR_STOP=1 \
  -c "DROP DATABASE IF EXISTS ${required_database} WITH (FORCE)" >/dev/null
psql "${psql_maintenance_url}" -v ON_ERROR_STOP=1 \
  -c "CREATE DATABASE ${required_database}" >/dev/null
database_created=1

frontend_origin="http://127.0.0.1:4273"
api_origin="http://127.0.0.1:8180"
fernet_key="$(.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
export APP_ENV=test
export DATABASE_URL="${performance_database_url}"
export MOCKINTERVIEW_MIGRATION_DATABASE_URL="${performance_database_url}"
export GOOGLE_OIDC_CLIENT_ID=performance-client
export GOOGLE_OIDC_CLIENT_SECRET=performance-secret
export GOOGLE_OIDC_ISSUER=https://accounts.google.com
export GOOGLE_OIDC_REDIRECT_URI="${api_origin}/api/v1/auth/google/callback"
export OAUTH_TRANSACTION_ENCRYPTION_KEYS="performance=${fernet_key}"
export OAUTH_TRANSACTION_TTL_SECONDS=300
export OAUTH_RETURN_PATHS=/candidate,/manager,/admin
export SESSION_ABSOLUTE_SECONDS=28800
export SESSION_IDLE_SECONDS=7200
export SESSION_COOKIE_NAME=mi_perf_session
export SESSION_COOKIE_SECURE=false
export FRONTEND_ORIGINS="[\"${frontend_origin}\"]"
export CSRF_ALLOWED_ORIGINS="[\"${frontend_origin}\"]"
export FRONTEND_APPLICATION_ORIGIN="${frontend_origin}"
export ENABLE_FAKE_OIDC=true
export PERFORMANCE_STATE_DIR="${state_dir}"
export PERFORMANCE_FRONTEND_ORIGIN="${frontend_origin}"
export VITE_API_PROXY_TARGET="${api_origin}"

.venv/bin/alembic -c apps/api/alembic.ini upgrade head
.venv/bin/python apps/api/scripts/seed_role_interview_performance.py \
  --database-url "${performance_database_url}" --state-dir "${state_dir}"
.venv/bin/python apps/api/scripts/role_interview_baseline.py \
  --database-url "${performance_database_url}" --output "${state_dir}/backend-baseline.json"

npm --prefix apps/web run build
.venv/bin/uvicorn app.main:build_app --factory --app-dir apps/api \
  --host 127.0.0.1 --port 8180 >"${state_dir}/api.log" 2>&1 &
api_pid=$!
npm --prefix apps/web run preview -- --port 4273 --strictPort \
  >"${state_dir}/preview.log" 2>&1 &
preview_pid=$!

for attempt in {1..60}; do
  if curl --fail --silent "${api_origin}/health" >/dev/null; then break; fi
  if [[ "${attempt}" -eq 60 ]]; then
    echo "API health check failed" >&2
    exit 1
  fi
  sleep 1
done
for attempt in {1..60}; do
  if curl --fail --silent "${frontend_origin}/" >/dev/null; then break; fi
  if [[ "${attempt}" -eq 60 ]]; then
    echo "Preview health check failed" >&2
    exit 1
  fi
  sleep 1
done

(
  cd apps/web
  npx playwright test --config playwright.performance.config.ts
)

evidence_dir="specs/002-role-interview-management/evidence"
mkdir -p "${evidence_dir}"
install -m 600 "${state_dir}/backend-baseline.json" "${evidence_dir}/backend-baseline.json"
install -m 600 "${state_dir}/browser-performance.json" "${evidence_dir}/browser-performance.json"
.venv/bin/python - "${evidence_dir}/backend-baseline.json" "${evidence_dir}/browser-performance.json" <<'PY'
import json
import sys
from pathlib import Path

for filename in sys.argv[1:]:
    data = json.loads(Path(filename).read_text(encoding="utf-8"))
    print(json.dumps({"evidence": filename, "results": data["results"]}, indent=2))
PY
