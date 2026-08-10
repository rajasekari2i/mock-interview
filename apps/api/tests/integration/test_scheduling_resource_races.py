from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest
from app.auth.errors import AuthError, ErrorCode
from app.auth.models import EntityStatus, Role, User
from app.interviews.models import ScheduledInterview
from app.interviews.service import schedule_interview
from app.jds.models import JobDescription
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.mark.asyncio
@pytest.mark.parametrize("resource", ["candidate", "manager", "job"])
@pytest.mark.parametrize("mutation_first", [True, False])
async def test_scheduling_serializes_both_lock_orders_for_resource_loss(
    migrated_database_url: str,
    factories: object,
    clock: object,
    resource: str,
    mutation_first: bool,
) -> None:
    engine = create_async_engine(migrated_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE audit_events, scheduled_interviews, job_descriptions, "
                "external_login_identities, candidate_profiles, authentication_sessions, users, "
                "organization_domain_mappings, organizations, oauth_transactions CASCADE"
            )
        )
    organization = factories.organization()
    manager = factories.user(organization=organization, role=Role.MANAGER.value)
    other_manager = factories.user(organization=organization, role=Role.MANAGER.value)
    candidate = factories.user(organization=organization, role=Role.CANDIDATE.value)
    async with sessions.begin() as seed:
        seed.add_all([organization, manager, other_manager, candidate])
        await seed.flush()
        job = factories.job_description(organization=organization, creator=manager)
        seed.add_all(
            [factories.candidate_profile(organization=organization, user=candidate), job]
        )

    async def schedule() -> ScheduledInterview:
        async with sessions.begin() as session:
            record, replayed = await schedule_interview(
                session,
                org_id=organization.id,
                manager_user_id=manager.id,
                candidate_user_id=candidate.id,
                job_description_id=job.id,
                scheduled_at=clock.now() + timedelta(hours=1),
                idempotency_key=f"{resource}-{mutation_first}",
                now=clock.now(),
                correlation_id="race-test",
            )
            assert not replayed
            return record

    async def mutate() -> None:
        async with sessions.begin() as session:
            if resource == "job":
                row = await session.get(JobDescription, job.id, with_for_update=True)
                assert row is not None
                row.created_by_user_id = other_manager.id
            else:
                user_id = candidate.id if resource == "candidate" else manager.id
                row = await session.get(User, user_id, with_for_update=True)
                assert row is not None
                row.status = EntityStatus.DISABLED.value
            await session.flush()

    async with sessions() as locking_session:
        await locking_session.begin()
        if mutation_first:
            if resource == "job":
                locked = await locking_session.get(JobDescription, job.id, with_for_update=True)
                assert locked is not None
                locked.created_by_user_id = other_manager.id
            else:
                user_id = candidate.id if resource == "candidate" else manager.id
                locked = await locking_session.get(User, user_id, with_for_update=True)
                assert locked is not None
                locked.status = EntityStatus.DISABLED.value
            await locking_session.flush()
            pending = asyncio.create_task(schedule())
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(asyncio.shield(pending), timeout=0.05)
            await locking_session.commit()
            with pytest.raises(AuthError) as unavailable:
                await pending
            assert unavailable.value.code is ErrorCode.RESOURCE_NOT_FOUND
        else:
            record, replayed = await schedule_interview(
                locking_session,
                org_id=organization.id,
                manager_user_id=manager.id,
                candidate_user_id=candidate.id,
                job_description_id=job.id,
                scheduled_at=clock.now() + timedelta(hours=1),
                idempotency_key=f"{resource}-{mutation_first}",
                now=clock.now(),
                correlation_id="race-test",
            )
            assert not replayed and record.id is not None
            pending = asyncio.create_task(mutate())
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(asyncio.shield(pending), timeout=0.05)
            await locking_session.commit()
            if resource == "job":
                with pytest.raises(IntegrityError):  # final fail-closed database defense
                    await pending
            else:
                await pending

    async with sessions() as verification:
        count = int(await verification.scalar(select(func.count(ScheduledInterview.id))) or 0)
    assert count == (0 if mutation_first else 1)
    await engine.dispose()
