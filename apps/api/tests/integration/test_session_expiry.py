from __future__ import annotations

from datetime import timedelta

import pytest
from app.auth.errors import AuthError, ErrorCode
from app.auth.sessions import create_session, resolve_session
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("deadline", "delta"),
    [
        ("idle", timedelta(microseconds=-1)),
        ("idle", timedelta()),
        ("idle", timedelta(microseconds=1)),
        ("absolute", timedelta(microseconds=-1)),
        ("absolute", timedelta()),
        ("absolute", timedelta(microseconds=1)),
    ],
)
async def test_session_deadline_boundaries(
    deadline: str,
    delta: timedelta,
    db_session: AsyncSession,
    factories: object,
    clock: object,
) -> None:
    organization = factories.organization()
    user = factories.user(organization=organization)
    db_session.add_all([organization, user])
    await db_session.flush()
    created = await create_session(db_session, user, now=clock.now())
    if deadline == "absolute":
        created.record.idle_expires_at = created.record.absolute_expires_at
        boundary = created.record.absolute_expires_at
    else:
        boundary = created.record.idle_expires_at
    instant = boundary + delta

    if delta < timedelta():
        assert (await resolve_session(db_session, created.token, now=instant))[1].id == user.id
    else:
        with pytest.raises(AuthError) as error:
            await resolve_session(db_session, created.token, now=instant)
        assert error.value.code is ErrorCode.SESSION_EXPIRED
