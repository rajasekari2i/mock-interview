# Dependency License Review

The approved SPDX expressions below apply to the direct dependencies pinned in the backend and
frontend manifests. Transitive lockfile contents must be re-audited before release. New or changed
dependencies require a reviewed entry before installation.

Approved license expressions: `MIT`, `BSD-3-Clause`, `Apache-2.0`,
`Apache-2.0 OR BSD-3-Clause`, and `LGPL-3.0-only`.

| Dependency | SPDX | Scope | Rationale |
|---|---|---|---|
| alembic | MIT | runtime/tooling | Versioned PostgreSQL migrations |
| authlib | BSD-3-Clause | runtime | Maintained OAuth/OIDC client and claim verification |
| cryptography | Apache-2.0 OR BSD-3-Clause | runtime | PKCE verifier encryption with key rotation |
| email-validator | CC0-1.0 | runtime | Pydantic email boundary validation; permissive public-domain dedication |
| fastapi | MIT | runtime | Typed HTTP application boundary |
| psycopg | LGPL-3.0-only | runtime | PostgreSQL async driver |
| pydantic-settings | MIT | runtime | Typed environment validation |
| sqlalchemy | MIT | runtime | Typed relational persistence |
| uvicorn | BSD-3-Clause | runtime | ASGI server |
| setuptools | MIT | build | Standards-based Python package build backend |
| httpx | BSD-3-Clause | test | API and adapter testing |
| mypy | MIT | tooling | Strict Python type checking |
| pytest | MIT | test | Backend test runner |
| pytest-asyncio | Apache-2.0 | test | Deterministic async tests |
| pytest-cov | MIT | test | Coverage enforcement |
| ruff | MIT | tooling | Python lint and format checks |
| types-pyyaml | Apache-2.0 | tooling | Static typing metadata for YAML boundaries |
| react | MIT | runtime | UI framework |
| react-dom | MIT | runtime | Browser renderer |
| react-router-dom | MIT | runtime | Role-aware routing |
| vite | MIT | tooling | Frontend build and development server |
| vitest | MIT | test | Frontend unit and coverage runner |
| @vitest/coverage-v8 | MIT | test | V8 coverage integration |
| @playwright/test | Apache-2.0 | test | Browser journey testing |
| @testing-library/react | MIT | test | Accessible component tests |
| @testing-library/jest-dom | MIT | test | DOM assertions |
| @testing-library/user-event | MIT | test | User interaction tests |
| axe-core | MPL-2.0 | test | Accessibility rules; file-level copyleft remains within the dependency |
| @eslint/js | MIT | tooling | ESLint core recommended configuration |
| eslint-plugin-react-hooks | MIT | tooling | React hook correctness rules |
| eslint-plugin-react-refresh | MIT | tooling | Safe React refresh exports |
| eslint | MIT | tooling | TypeScript/React linting |
| globals | MIT | tooling | Browser and Node lint globals |
| jsdom | MIT | test | Component DOM test environment |
| typescript | Apache-2.0 | tooling | Strict TypeScript checking |
| typescript-eslint | MIT | tooling | Type-aware TypeScript linting |
| @vitejs/plugin-react | MIT | tooling | React compilation for Vite |
| @types/node | MIT | tooling | Node TypeScript declarations |
| @types/react | MIT | tooling | React TypeScript declarations |
| @types/react-dom | MIT | tooling | React DOM TypeScript declarations |

The allowlist also permits `CC0-1.0` and `MPL-2.0` for the specifically reviewed packages above.
