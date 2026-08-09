from __future__ import annotations

import pytest
from app.admin.service import change_user_role, change_user_status, remove_domain_mapping
from app.auth.errors import AuthError, ErrorCode
from app.auth.models import EntityStatus, Role
from app.auth.sessions import create_session, resolve_session
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["role", "disable"])
async def test_admin_security_mutation_revokes_two_sessions(
    mutation: str, db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    admin = factories.user(organization=organization, role=Role.ADMIN.value)
    user = factories.user(organization=organization)
    db_session.add_all([organization, admin, user])
    await db_session.flush()
    sessions = [
        await create_session(db_session, user, now=clock.now()),
        await create_session(db_session, user, now=clock.now()),
    ]

    if mutation == "role":
        await change_user_role(
            db_session,
            user_id=user.id,
            role=Role.ADMIN,
            actor_user_id=admin.id,
            correlation_id="role-revoke",
            now=clock.now(),
        )
    else:
        await change_user_status(
            db_session,
            user_id=user.id,
            status=EntityStatus.DISABLED,
            actor_user_id=admin.id,
            correlation_id="disable-revoke",
            now=clock.now(),
        )

    for created in sessions:
        with pytest.raises(AuthError) as denied:
            await resolve_session(db_session, created.token, now=clock.now())
        assert denied.value.code is ErrorCode.SESSION_REVOKED


@pytest.mark.asyncio
async def test_reenable_requires_a_new_login(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    admin = factories.user(organization=organization, role=Role.ADMIN.value)
    user = factories.user(organization=organization)
    db_session.add_all([organization, admin, user])
    await db_session.flush()
    old = await create_session(db_session, user, now=clock.now())
    for status in (EntityStatus.DISABLED, EntityStatus.ACTIVE):
        await change_user_status(
            db_session,
            user_id=user.id,
            status=status,
            actor_user_id=admin.id,
            correlation_id=f"status-{status.value}",
            now=clock.now(),
        )

    with pytest.raises(AuthError):
        await resolve_session(db_session, old.token, now=clock.now())
    fresh = await create_session(db_session, user, now=clock.now())
    assert (await resolve_session(db_session, fresh.token, now=clock.now()))[1].id == user.id


@pytest.mark.asyncio
async def test_mapping_removal_revokes_every_old_cookie_but_not_independent_user(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    mapping = factories.domain_mapping(organization=organization)
    mapped = factories.user(
        organization=organization,
        role=Role.CANDIDATE.value,
        registration_domain_mapping_id=mapping.id,
    )
    independent = factories.user(organization=organization)
    db_session.add_all([organization, mapping, mapped, independent])
    await db_session.flush()
    db_session.add(factories.candidate_profile(organization=organization, user=mapped))
    old_sessions = [
        await create_session(db_session, mapped, now=clock.now()),
        await create_session(db_session, mapped, now=clock.now()),
    ]
    unaffected = await create_session(db_session, independent, now=clock.now())
    await remove_domain_mapping(
        db_session,
        mapping_id=mapping.id,
        actor_user_id=None,
        correlation_id="multi-session-remove",
        now=clock.now(),
    )
    for created in old_sessions:
        with pytest.raises(AuthError) as denied:
            await resolve_session(db_session, created.token, now=clock.now())
        assert denied.value.code is ErrorCode.SESSION_REVOKED
    unaffected_user = (
        await resolve_session(db_session, unaffected.token, now=clock.now())
    )[1]
    assert unaffected_user.id == independent.id
