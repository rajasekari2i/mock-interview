from __future__ import annotations

from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from app.auth.errors import AuthError, ErrorCode
from app.interviews.tenancy import ScheduledInterviewTenantMigrationParticipant


@pytest.mark.asyncio
async def test_participant_allows_no_records_and_blocks_multi_owner_records() -> None:
    participant = ScheduledInterviewTenantMigrationParticipant()
    session = AsyncMock()
    session.execute.return_value = Mock(all=Mock(return_value=[]))
    await participant.validate_and_lock(session, (UUID(int=1),), UUID(int=2), UUID(int=3))
    assert await participant.migrate(session, (UUID(int=1),), UUID(int=2), UUID(int=3), Mock()) == 0

    session.execute.return_value = Mock(all=Mock(return_value=[(UUID(int=4),)]))
    with pytest.raises(AuthError) as error:
        await participant.validate_and_lock(session, (UUID(int=1),), UUID(int=2), UUID(int=3))
    assert error.value.code is ErrorCode.IDENTITY_CONFLICT


@pytest.mark.asyncio
async def test_participant_skips_query_for_an_empty_candidate_set() -> None:
    participant = ScheduledInterviewTenantMigrationParticipant()
    session = AsyncMock()
    await participant.validate_and_lock(session, (), UUID(int=2), UUID(int=3))
    session.execute.assert_not_awaited()
