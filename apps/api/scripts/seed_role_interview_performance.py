"""Seed the isolated role/interview performance database deterministically."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid5

from app.auth.models import CandidateProfile, EntityStatus, Organization, Role, User
from app.auth.sessions import create_session
from app.interviews.models import InterviewStatus, ScheduledInterview
from app.interviews.service import idempotency_digest, request_fingerprint
from app.jds.models import JobDescription, JobDescriptionSourceType
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

NAMESPACE = UUID("a54f746d-78b4-4c71-92c7-84e8b0afcb3e")
USER_COUNT = 1_000
JD_COUNT = 1_000


def stable_id(value: str) -> UUID:
    return uuid5(NAMESPACE, value)


async def seed(database_url: str, state_dir: Path) -> dict[str, object]:
    if state_dir.stat().st_mode & 0o077:
        raise RuntimeError("Performance state directory must not be accessible by group or others")
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)
    organization = Organization(
        id=stable_id("organization"),
        name="Role Interview Performance",
        slug="role-interview-performance",
        status=EntityStatus.ACTIVE.value,
        created_at=now,
        updated_at=now,
    )
    users: list[User] = []
    for index in range(USER_COUNT):
        role = Role.CANDIDATE if index < 700 else Role.MANAGER if index < 999 else Role.ADMIN
        users.append(
            User(
                id=stable_id(f"user-{index}"),
                org_id=organization.id,
                email=f"performance-{index:04d}@example.test",
                normalized_email=f"performance-{index:04d}@example.test",
                display_name=f"Performance User {index:04d}",
                profile_picture_url=None,
                role=role.value,
                status=EntityStatus.ACTIVE.value,
                auth_generation=1,
                registration_domain_mapping_id=None,
                created_at=now,
                updated_at=now,
            )
        )
    candidate = users[0]
    manager = users[700]
    admin = users[-1]
    job_descriptions = [
        JobDescription(
            id=stable_id(f"jd-{index}"),
            org_id=organization.id,
            created_by_user_id=manager.id,
            title=f"Performance Job Description {index:04d}",
            source_type=JobDescriptionSourceType.MANUAL.value,
            content_text=f"Deterministic performance content {index:04d}.",
            source_format=None,
            created_at=now - timedelta(seconds=index),
            updated_at=now,
        )
        for index in range(JD_COUNT)
    ]
    async with session_factory.begin() as session:
        if int(await session.scalar(select(func.count(User.id))) or 0) != 0:
            raise RuntimeError("Performance database must be empty before seeding")
        session.add(organization)
        await session.flush()
        session.add_all(users)
        await session.flush()
        session.add_all(
            CandidateProfile(
                id=stable_id(f"candidate-profile-{index}"),
                org_id=organization.id,
                user_id=users[index].id,
                created_at=now,
                updated_at=now,
            )
            for index in range(700)
        )
        session.add_all(job_descriptions)
        await session.flush()
        scheduled_at = now + timedelta(days=7)
        session.add(
            ScheduledInterview(
                id=stable_id("interview-0"),
                org_id=organization.id,
                candidate_user_id=candidate.id,
                job_description_id=job_descriptions[0].id,
                scheduling_manager_user_id=manager.id,
                scheduled_at=scheduled_at,
                status=InterviewStatus.SCHEDULED.value,
                idempotency_key_digest=idempotency_digest("performance-interview-0"),
                request_fingerprint=request_fingerprint(
                    candidate.id, job_descriptions[0].id, scheduled_at
                ),
                created_at=now,
                updated_at=now,
            )
        )
        session_states: dict[str, object] = {}
        for role, user, home_path in (
            (Role.CANDIDATE, candidate, "/candidate"),
            (Role.MANAGER, manager, "/manager"),
            (Role.ADMIN, admin, "/admin"),
        ):
            created = await create_session(session, user, now=now)
            session_states[role.value] = {
                "token": created.token,
                "csrfToken": created.csrf_token,
                "homePath": home_path,
            }
    result = {
        "schemaVersion": 1,
        "cookieName": "mi_perf_session",
        "csrfCookieName": "mi_csrf",
        "sessions": session_states,
        "counts": {"users": USER_COUNT, "jobDescriptions": JD_COUNT},
    }
    state_path = state_dir / "sessions.json"
    state_path.write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")
    os.chmod(state_path, 0o600)
    await engine.dispose()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--state-dir", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.database_url is None:
        parser.error("--database-url or DATABASE_URL is required")
    result = asyncio.run(seed(arguments.database_url, arguments.state_dir))
    print(json.dumps({"counts": result["counts"], "stateFile": "sessions.json"}))


if __name__ == "__main__":
    main()
