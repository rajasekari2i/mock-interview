"""Measure read-only role-home queries against the deterministic 1,000-record fixture."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import time
from datetime import UTC, datetime
from pathlib import Path
from statistics import median

from app.admin.service import list_admin_job_descriptions, list_admin_users
from app.auth.models import Role, User
from app.interviews.service import list_candidate_interviews
from app.jds.service import list_manager_job_descriptions
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[min(len(values) - 1, int((len(values) - 1) * fraction))]


async def run(database_url: str, samples: int) -> dict[str, object]:
    engine = create_async_engine(database_url, pool_size=10, max_overflow=0)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        candidate = await session.scalar(select(User).where(User.role == Role.CANDIDATE.value))
        manager = await session.scalar(select(User).where(User.role == Role.MANAGER.value))
        if candidate is None or manager is None:
            raise RuntimeError("Run seed_role_interview_performance.py before the baseline")

    latencies: dict[str, list[float]] = {
        "candidateHome": [],
        "managerHome": [],
        "adminUsers": [],
        "adminJds": [],
    }

    async def measure(operation: str, index: int) -> None:
        started = time.perf_counter()
        async with factory() as session:
            if operation == "candidateHome":
                _, total = await list_candidate_interviews(
                    session,
                    candidate_user_id=candidate.id,
                    org_id=candidate.org_id,
                    page=1,
                    page_size=25,
                )
                if total < 1:
                    raise RuntimeError("Candidate fixture has no scheduled interview")
            elif operation == "managerHome":
                _, total = await list_manager_job_descriptions(
                    session,
                    org_id=manager.org_id,
                    manager_user_id=manager.id,
                    page=(index % 40) + 1,
                    page_size=25,
                )
                if total != 1_000:
                    raise RuntimeError("Manager fixture must own exactly 1,000 JDs")
            elif operation == "adminUsers":
                _, total = await list_admin_users(session, page=(index % 40) + 1, page_size=25)
                if total != 1_000:
                    raise RuntimeError("Admin fixture must contain exactly 1,000 users")
            else:
                _, total = await list_admin_job_descriptions(
                    session, page=(index % 40) + 1, page_size=25
                )
                if total != 1_000:
                    raise RuntimeError("Admin fixture must contain exactly 1,000 JDs")
        latencies[operation].append((time.perf_counter() - started) * 1_000)

    operations = tuple(latencies)
    for start in range(0, samples, 10):
        end = min(start + 10, samples)
        await asyncio.gather(
            *(measure(operations[index % len(operations)], index) for index in range(start, end))
        )
    async with factory() as session:
        database_version = str(await session.scalar(text("select version()")))
    await engine.dispose()
    return {
        "schemaVersion": 1,
        "recordedAt": datetime.now(UTC).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "databaseVersion": database_version,
        },
        "configuration": {
            "samples": samples,
            "concurrency": 10,
            "users": 1_000,
            "jobDescriptions": 1_000,
        },
        "results": {
            name: {
                "samples": len(values),
                "p50Milliseconds": median(values),
                "p95Milliseconds": percentile(values, 0.95),
                "maxMilliseconds": max(values),
                "failures": 0,
            }
            for name, values in latencies.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.database_url is None:
        parser.error("--database-url or DATABASE_URL is required")
    if arguments.samples < 100:
        parser.error("--samples must be at least 100")
    result = asyncio.run(run(arguments.database_url, arguments.samples))
    serialized = json.dumps(result, indent=2) + "\n"
    if arguments.output is None:
        print(serialized, end="")
    else:
        arguments.output.write_text(serialized, encoding="utf-8")


if __name__ == "__main__":
    main()
