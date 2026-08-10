from __future__ import annotations

import asyncio

import pytest
from app.admin.service import (
    create_domain_mapping,
    reassign_domain_mapping,
    remove_domain_mapping,
)
from app.auth.errors import AuthError, ErrorCode
from app.auth.google_oidc import GoogleClaims
from app.auth.models import EntityStatus, User
from app.auth.service import acquire_domain_lock, resolve_or_bind_identity
from app.tenancy.coordinator import CandidateTenantMigrationCoordinator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.mark.asyncio
async def test_registration_then_removal_serializes_to_fully_disabled_candidate(
    db_session: object,
    factories: object,
    clock: object,
    migrated_database_url: str,
) -> None:
    organization = factories.organization()
    mapping = factories.domain_mapping(organization=organization)
    db_session.add_all([organization, mapping])
    await db_session.commit()
    engine = create_async_engine(migrated_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def remove_after_lock() -> None:
        async with sessions.begin() as session:
            await remove_domain_mapping(
                session,
                mapping_id=mapping.id,
                actor_user_id=None,
                correlation_id="concurrent-remove",
                now=clock.now(),
            )

    async with sessions.begin() as registration_session:
        await acquire_domain_lock(registration_session, "example.test")
        removal = asyncio.create_task(remove_after_lock())
        await asyncio.sleep(0)
        registered = await resolve_or_bind_identity(
            registration_session,
            GoogleClaims(
                "https://accounts.google.com",
                "concurrent-subject",
                "concurrent@example.test",
                "Concurrent Candidate",
            ),
            now=clock.now(),
        )
    await asyncio.wait_for(removal, timeout=5)
    async with sessions() as verification:
        user = await verification.get(User, registered.id)
        assert user is not None
        assert user.status == EntityStatus.DISABLED.value
        assert user.auth_generation == 2
    await engine.dispose()


@pytest.mark.asyncio
async def test_removal_then_registration_observes_removed_mapping(
    db_session: object,
    factories: object,
    clock: object,
    migrated_database_url: str,
) -> None:
    organization = factories.organization()
    mapping = factories.domain_mapping(organization=organization)
    db_session.add_all([organization, mapping])
    await db_session.commit()
    engine = create_async_engine(migrated_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def register_after_lock() -> ErrorCode:
        try:
            async with sessions.begin() as session:
                await resolve_or_bind_identity(
                    session,
                    GoogleClaims(
                        "https://accounts.google.com",
                        "late-subject",
                        "late@example.test",
                    ),
                    now=clock.now(),
                )
        except AuthError as error:
            return error.code
        raise AssertionError("registration unexpectedly succeeded")

    async with sessions.begin() as removal_session:
        await remove_domain_mapping(
            removal_session,
            mapping_id=mapping.id,
            actor_user_id=None,
            correlation_id="remove-first",
            now=clock.now(),
        )
        registration = asyncio.create_task(register_after_lock())
        await asyncio.sleep(0)
    assert await asyncio.wait_for(registration, timeout=5) is ErrorCode.ACCESS_NOT_PROVISIONED
    async with sessions() as verification:
        users = list(
            (
                await verification.scalars(
                    select(User).where(User.normalized_email == "late@example.test")
                )
            ).all()
        )
        assert users == []
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_then_registration_observes_complete_new_mapping(
    db_session: object,
    factories: object,
    clock: object,
    migrated_database_url: str,
) -> None:
    organization = factories.organization()
    db_session.add(organization)
    await db_session.commit()
    engine = create_async_engine(migrated_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def register() -> User:
        async with sessions.begin() as session:
            return await resolve_or_bind_identity(
                session,
                GoogleClaims(
                    "https://accounts.google.com",
                    "created-mapping-subject",
                    "created@example.test",
                ),
                now=clock.now(),
            )

    async with sessions.begin() as create_session:
        await create_domain_mapping(
            create_session,
            domain="example.test",
            organization_id=organization.id,
            actor_user_id=None,
            correlation_id="create-first",
            now=clock.now(),
        )
        registration = asyncio.create_task(register())
        await asyncio.sleep(0)
    registered = await asyncio.wait_for(registration, timeout=5)
    assert registered.org_id == organization.id
    await engine.dispose()


@pytest.mark.asyncio
async def test_reassignment_then_registration_observes_complete_target_mapping(
    db_session: object,
    factories: object,
    clock: object,
    migrated_database_url: str,
) -> None:
    source = factories.organization()
    target = factories.organization()
    mapping = factories.domain_mapping(organization=source)
    db_session.add_all([source, target, mapping])
    await db_session.commit()
    engine = create_async_engine(migrated_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def register() -> User:
        async with sessions.begin() as session:
            return await resolve_or_bind_identity(
                session,
                GoogleClaims(
                    "https://accounts.google.com",
                    "reassigned-mapping-subject",
                    "reassigned@example.test",
                ),
                now=clock.now(),
            )

    async with sessions.begin() as reassign_session:
        await reassign_domain_mapping(
            reassign_session,
            mapping_id=mapping.id,
            target_organization_id=target.id,
            coordinator=CandidateTenantMigrationCoordinator(),
            actor_user_id=None,
            correlation_id="reassign-first",
            now=clock.now(),
        )
        registration = asyncio.create_task(register())
        await asyncio.sleep(0)
    registered = await asyncio.wait_for(registration, timeout=5)
    assert registered.org_id == target.id
    await engine.dispose()
