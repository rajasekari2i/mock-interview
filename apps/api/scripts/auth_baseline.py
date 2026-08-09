"""Run the fixed, non-blocking PostgreSQL authentication baseline."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from uuid import uuid4

from app.auth.errors import AuthError
from app.auth.google_oidc import GoogleClaims
from app.auth.models import (
    AuditEvent,
    AuthenticationSession,
    CandidateProfile,
    EntityStatus,
    ExternalLoginIdentity,
    Organization,
    OrganizationDomainMapping,
    Role,
    User,
)
from app.auth.policies import AuthContext, Capability, ResourceScope, authorize
from app.auth.service import resolve_or_bind_identity
from app.auth.sessions import create_session, resolve_session
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def percentile(values: list[float], percentage: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, int((len(ordered) - 1) * percentage))
    return ordered[index]


async def run_baseline(
    *,
    database_url: str,
    warmup_seconds: int,
    duration_seconds: int,
    concurrency: int,
    seeded_sessions: int,
) -> dict[str, object]:
    engine = create_async_engine(database_url, pool_size=concurrency, max_overflow=0)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)
    organization = Organization(
        name="Authentication Baseline",
        slug=f"auth-baseline-{uuid4().hex}",
        status=EntityStatus.ACTIVE.value,
        created_at=now,
        updated_at=now,
    )
    email = f"baseline-{uuid4().hex}@example.test"
    user = User(
        org_id=organization.id,
        email=email,
        normalized_email=email,
        display_name="Baseline Manager",
        role=Role.MANAGER.value,
        status=EntityStatus.ACTIVE.value,
        auth_generation=1,
        created_at=now,
        updated_at=now,
    )
    mapping = OrganizationDomainMapping(
        org_id=organization.id,
        normalized_domain="baseline.test",
        removed_at=None,
        created_at=now,
        updated_at=now,
    )
    async with sessions.begin() as session:
        session.add(organization)
        await session.flush()
        user.org_id = organization.id
        mapping.org_id = organization.id
        session.add_all([user, mapping])
        await session.flush()
        await resolve_or_bind_identity(
            session,
            GoogleClaims(
                "https://accounts.google.com",
                "baseline-known-subject",
                email,
                "Baseline Manager",
            ),
            now=now,
            correlation_id="baseline-known-bind",
        )
        tokens = [
            (await create_session(session, user, now=now)).token for _ in range(seeded_sessions)
        ]

    latencies: list[float] = []
    outcomes: Counter[str] = Counter()
    sequence = 0
    sequence_lock = asyncio.Lock()

    async def one_request(record: bool) -> None:
        nonlocal sequence
        async with sequence_lock:
            current = sequence
            sequence += 1
        mix_slot = current % 100
        operation = (
            "auth-me"
            if mix_slot < 50
            else "allowed"
            if mix_slot < 65
            else "denied"
            if mix_slot < 80
            else "known-login"
            if mix_slot < 90
            else "mapped-first-login"
        )
        started = time.perf_counter()
        expected = True
        try:
            async with sessions.begin() as session:
                if operation == "known-login":
                    resolved_user = await resolve_or_bind_identity(
                        session,
                        GoogleClaims(
                            "https://accounts.google.com",
                            "baseline-known-subject",
                            email,
                        ),
                        now=datetime.now(UTC),
                        correlation_id="baseline-known-login",
                    )
                    expected = resolved_user.id == user.id
                elif operation == "mapped-first-login":
                    registered = await resolve_or_bind_identity(
                        session,
                        GoogleClaims(
                            "https://accounts.google.com",
                            f"baseline-candidate-{current}",
                            f"candidate-{current}@baseline.test",
                        ),
                        now=datetime.now(UTC),
                        correlation_id="baseline-mapped-login",
                    )
                    expected = (
                        registered.role == Role.CANDIDATE.value
                        and registered.registration_domain_mapping_id == mapping.id
                    )
                else:
                    _, resolved_user = await resolve_session(
                        session, tokens[current % len(tokens)], now=datetime.now(UTC)
                    )
                    if operation != "auth-me":
                        decision = authorize(
                            AuthContext(
                                resolved_user.id,
                                resolved_user.org_id,
                                Role(resolved_user.role),
                                None,
                            ),
                            ResourceScope(
                                resolved_user.org_id,
                                Capability.MANAGER_UPLOAD_JD
                                if operation == "allowed"
                                else Capability.ADMIN_MANAGE_USERS,
                            ),
                        )
                        expected = decision.allowed is (operation == "allowed")
        except AuthError:
            expected = False
        if record:
            latencies.append((time.perf_counter() - started) * 1000)
            outcomes[f"{operation}:{'expected' if expected else 'unexpected'}"] += 1

    async def phase(seconds: int, *, record: bool) -> None:
        deadline = time.monotonic() + seconds

        async def worker() -> None:
            while time.monotonic() < deadline:
                await one_request(record)

        await asyncio.gather(*(worker() for _ in range(concurrency)))

    try:
        await phase(warmup_seconds, record=False)
        measured_start = time.perf_counter()
        await phase(duration_seconds, record=True)
        elapsed = time.perf_counter() - measured_start
        async with sessions() as session:
            postgres_version = str(await session.scalar(text("select version()")))
        result: dict[str, object] = {
            "schemaVersion": 1,
            "recordedAt": datetime.now(UTC).isoformat(),
            "buildIdentifier": os.environ.get("GITHUB_SHA", "local-working-tree"),
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "database": "PostgreSQL",
                "databaseVersion": postgres_version,
            },
            "configuration": {
                "warmupSeconds": warmup_seconds,
                "durationSeconds": duration_seconds,
                "concurrency": concurrency,
                "seededSessions": seeded_sessions,
                "requestMix": {
                    "auth-me": 50,
                    "allowed": 15,
                    "denied": 15,
                    "known-login": 10,
                    "mapped-first-login": 10,
                },
            },
            "results": {
                "requests": len(latencies),
                "throughputPerSecond": len(latencies) / elapsed,
                "latencyMilliseconds": {
                    "p50": median(latencies),
                    "p95": percentile(latencies, 0.95),
                },
                "outcomes": dict(sorted(outcomes.items())),
            },
            "numericGateApplied": False,
        }
        if any(key.endswith(":unexpected") and value for key, value in outcomes.items()):
            raise RuntimeError("Authentication baseline encountered unexpected outcomes")
        return result
    finally:
        async with sessions.begin() as session:
            for model in (
                AuthenticationSession,
                ExternalLoginIdentity,
                CandidateProfile,
                AuditEvent,
            ):
                await session.execute(delete(model).where(model.org_id == organization.id))
            await session.execute(delete(User).where(User.org_id == organization.id))
            await session.execute(
                delete(OrganizationDomainMapping).where(
                    OrganizationDomainMapping.org_id == organization.id
                )
            )
            await session.execute(delete(Organization).where(Organization.id == organization.id))
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--warmup-seconds", type=int, default=10)
    parser.add_argument("--duration-seconds", type=int, default=60)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--seeded-sessions", type=int, default=100)
    parser.add_argument(
        "--mix",
        default="auth-me=50,allowed=15,denied=15,known-login=10,mapped-first-login=10",
    )
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.database_url is None:
        parser.error("--database-url or DATABASE_URL is required")
    fixed = (
        10,
        60,
        20,
        100,
        "auth-me=50,allowed=15,denied=15,known-login=10,mapped-first-login=10",
    )
    actual = (
        arguments.warmup_seconds,
        arguments.duration_seconds,
        arguments.concurrency,
        arguments.seeded_sessions,
        arguments.mix,
    )
    if actual != fixed:
        parser.error("V1 baseline configuration is fixed; request mix includes mapped login")
    result = asyncio.run(
        run_baseline(
            database_url=arguments.database_url,
            warmup_seconds=arguments.warmup_seconds,
            duration_seconds=arguments.duration_seconds,
            concurrency=arguments.concurrency,
            seeded_sessions=arguments.seeded_sessions,
        )
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
