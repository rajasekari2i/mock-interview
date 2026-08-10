#!/usr/bin/env bash
set -euo pipefail

quality_python="${MOCKINTERVIEW_PYTHON:-python3}"

if [[ -z "${TEST_DATABASE_URL:-}" ]]; then
  echo "TEST_DATABASE_URL is required and must identify a disposable test database." >&2
  exit 1
fi

if [[ -n "${DATABASE_URL:-}" && "$TEST_DATABASE_URL" == "$DATABASE_URL" ]]; then
  echo "TEST_DATABASE_URL must not equal DATABASE_URL." >&2
  exit 1
fi

bash scripts/check-dependency-licenses.sh
"$quality_python" -m ruff check apps/api
"$quality_python" -m mypy --config-file apps/api/pyproject.toml apps/api/app
"$quality_python" -m pytest \
  -c apps/api/pyproject.toml \
  --cov=apps/api/app \
  --cov-branch \
  --cov-config=apps/api/pyproject.toml \
  --cov-report=term-missing \
  --cov-report=json:.coverage-backend.json \
  --cov-fail-under=100 \
  apps/api/tests
"$quality_python" scripts/verify-backend-coverage.py

npm --prefix apps/web run lint
npm --prefix apps/web run typecheck
npm --prefix apps/web run test:coverage
npm --prefix apps/web run test:e2e
