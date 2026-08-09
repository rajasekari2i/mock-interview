from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.auth.errors import AuthError, ErrorCode
from app.auth.models import EntityStatus, RevocationReason
from app.auth.sessions import (
    IDLE_LIFETIME,
    create_session,
    resolve_session,
    revoke_all_sessions,
    token_digest,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_and_digest_resolution_refreshes_idle_without_crossing_absolute(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    user = factories.user(organization=organization)
    db_session.add_all([organization, user])
    await db_session.flush()

    created = await create_session(db_session, user, now=clock.now())
    clock.advance(hours=1)
    record, resolved_user = await resolve_session(db_session, created.token, now=clock.now())

    assert record.token_digest == token_digest(created.token)
    assert resolved_user.id == user.id
    assert record.last_activity_at == clock.now()
    assert record.idle_expires_at == clock.now() + IDLE_LIFETIME
    clock.advance(hours=7)
    with pytest.raises(AuthError) as expired:
        await resolve_session(db_session, created.token, now=clock.now())
    assert expired.value.code is ErrorCode.SESSION_EXPIRED
    assert record.revocation_reason == RevocationReason.ABSOLUTE_EXPIRED.value


@pytest.mark.asyncio
async def test_exact_idle_boundary_expires_and_records_reason(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    user = factories.user(organization=organization)
    db_session.add_all([organization, user])
    await db_session.flush()
    created = await create_session(db_session, user, now=clock.now())

    clock.advance(hours=2)
    with pytest.raises(AuthError) as expired:
        await resolve_session(db_session, created.token, now=clock.now())
    assert expired.value.code is ErrorCode.SESSION_EXPIRED
    assert created.record.revoked_at == clock.now()
    assert created.record.revocation_reason == RevocationReason.IDLE_EXPIRED.value


@pytest.mark.asyncio
async def test_generation_mismatch_and_disablement_are_revoked(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    user = factories.user(organization=organization)
    db_session.add_all([organization, user])
    await db_session.flush()
    generation_session = await create_session(db_session, user, now=clock.now())
    user.auth_generation += 1
    await db_session.flush()

    with pytest.raises(AuthError) as revoked:
        await resolve_session(db_session, generation_session.token, now=clock.now())
    assert revoked.value.code is ErrorCode.SESSION_REVOKED

    user.auth_generation -= 1
    user.status = EntityStatus.DISABLED.value
    await db_session.flush()
    with pytest.raises(AuthError) as disabled:
        await resolve_session(db_session, generation_session.token, now=clock.now())
    assert disabled.value.code is ErrorCode.SESSION_REVOKED


@pytest.mark.asyncio
async def test_revoke_all_is_global_idempotent_and_reenable_does_not_restore_sessions(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    user = factories.user(organization=organization)
    db_session.add_all([organization, user])
    await db_session.flush()
    first = await create_session(db_session, user, now=clock.now())
    second = await create_session(db_session, user, now=clock.now())

    assert await revoke_all_sessions(
        db_session,
        user_id=user.id,
        reason=RevocationReason.LOGOUT_ALL,
        now=clock.now(),
    ) == 2
    assert await revoke_all_sessions(
        db_session,
        user_id=user.id,
        reason=RevocationReason.LOGOUT_ALL,
        now=clock.now(),
    ) == 0
    user.status = EntityStatus.DISABLED.value
    user.status = EntityStatus.ACTIVE.value

    for token in (first.token, second.token):
        with pytest.raises(AuthError) as revoked:
            await resolve_session(db_session, token, now=clock.now())
        assert revoked.value.code is ErrorCode.SESSION_REVOKED


@pytest.mark.asyncio
async def test_unknown_session_token_requires_authentication(db_session: AsyncSession) -> None:
    with pytest.raises(AuthError) as error:
        await resolve_session(
            db_session,
            "not-a-session",
            now=datetime(2026, 8, 9, 9, 0, tzinfo=UTC),
        )
    assert error.value.code is ErrorCode.AUTHENTICATION_REQUIRED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reason",
    [
        RevocationReason.DOMAIN_MAPPING_REMOVED,
        RevocationReason.DOMAIN_MAPPING_REASSIGNED,
    ],
)
async def test_mapping_lifecycle_reasons_revoke_all_and_remain_terminal(
    reason: RevocationReason,
    db_session: AsyncSession,
    factories: object,
    clock: object,
) -> None:
    organization = factories.organization()
    user = factories.user(organization=organization)
    db_session.add_all([organization, user])
    await db_session.flush()
    created = [
        await create_session(db_session, user, now=clock.now()),
        await create_session(db_session, user, now=clock.now()),
    ]
    assert await revoke_all_sessions(
        db_session, user_id=user.id, reason=reason, now=clock.now()
    ) == 2
    assert await revoke_all_sessions(
        db_session, user_id=user.id, reason=reason, now=clock.now()
    ) == 0
    assert {item.record.revocation_reason for item in created} == {reason.value}
    for item in created:
        with pytest.raises(AuthError) as denied:
            await resolve_session(db_session, item.token, now=clock.now())
        assert denied.value.code is ErrorCode.SESSION_REVOKED
