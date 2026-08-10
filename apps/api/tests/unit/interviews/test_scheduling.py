from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from app.auth.errors import AuthError, ErrorCode
from app.interviews.service import idempotency_digest, request_fingerprint, validate_scheduled_at

NOW = datetime(2026, 8, 10, 9, 0, tzinfo=UTC)


def test_idempotency_digest_and_fingerprint_are_stable_and_scoped_to_payload() -> None:
    key = "00000000-0000-0000-0000-000000000001"
    assert idempotency_digest(key) == idempotency_digest(key)
    assert len(idempotency_digest(key)) == 32
    first = request_fingerprint(UUID(int=1), UUID(int=2), NOW + timedelta(hours=1))
    assert first == request_fingerprint(UUID(int=1), UUID(int=2), NOW + timedelta(hours=1))
    assert first != request_fingerprint(UUID(int=2), UUID(int=2), NOW + timedelta(hours=1))
    assert first != request_fingerprint(UUID(int=1), UUID(int=3), NOW + timedelta(hours=1))
    assert first != request_fingerprint(UUID(int=1), UUID(int=2), NOW + timedelta(hours=2))


def test_schedule_time_requires_an_offset_and_future_instant() -> None:
    assert validate_scheduled_at(NOW + timedelta(minutes=1), now=NOW) == NOW + timedelta(minutes=1)
    with pytest.raises(AuthError) as naive:
        validate_scheduled_at(datetime(2026, 8, 10, 10, 0), now=NOW)
    assert naive.value.code is ErrorCode.VALIDATION_ERROR
    with pytest.raises(AuthError) as past:
        validate_scheduled_at(NOW, now=NOW)
    assert past.value.code is ErrorCode.VALIDATION_ERROR
