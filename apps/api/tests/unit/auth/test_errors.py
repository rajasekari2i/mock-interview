from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import pytest
from app.auth.errors import (
    ERROR_DEFINITIONS,
    AuthError,
    ErrorCode,
    RecoveryAction,
    callback_error_redirect,
    encode_error,
)

EXPECTED = {
    ErrorCode.AUTHENTICATION_REQUIRED: (401, RecoveryAction.SIGN_IN_AGAIN),
    ErrorCode.SESSION_EXPIRED: (401, RecoveryAction.SIGN_IN_AGAIN),
    ErrorCode.SESSION_REVOKED: (401, RecoveryAction.SIGN_IN_AGAIN),
    ErrorCode.ACCESS_NOT_PROVISIONED: (403, RecoveryAction.CONTACT_ADMIN),
    ErrorCode.ACCOUNT_DISABLED: (403, RecoveryAction.CONTACT_ADMIN),
    ErrorCode.OAUTH_CANCELLED: (400, RecoveryAction.RETRY),
    ErrorCode.OAUTH_PROVIDER_UNAVAILABLE: (503, RecoveryAction.RETRY),
    ErrorCode.OAUTH_RESPONSE_INVALID: (400, RecoveryAction.RETRY),
    ErrorCode.FORBIDDEN: (403, RecoveryAction.GO_TO_ROLE_HOME),
    ErrorCode.CSRF_DENIED: (403, RecoveryAction.RETRY),
    ErrorCode.IDENTITY_CONFLICT: (409, RecoveryAction.CONTACT_ADMIN),
    ErrorCode.CANDIDATE_PROFILE_CONFLICT: (409, RecoveryAction.CONTACT_ADMIN),
    ErrorCode.VALIDATION_ERROR: (400, RecoveryAction.RETRY),
    ErrorCode.RESOURCE_NOT_FOUND: (404, RecoveryAction.GO_TO_ROLE_HOME),
}


def test_every_stable_error_has_one_safe_http_and_recovery_mapping() -> None:
    assert set(EXPECTED) == set(ErrorCode) == set(ERROR_DEFINITIONS)
    assert {
        code: (definition.http_status, definition.recovery)
        for code, definition in ERROR_DEFINITIONS.items()
    } == EXPECTED
    assert all(
        definition.message and "@" not in definition.message
        for definition in ERROR_DEFINITIONS.values()
    )


@pytest.mark.parametrize("code", ErrorCode)
def test_error_encoder_emits_only_the_stable_envelope(code: ErrorCode) -> None:
    error = AuthError(code)
    status, body = encode_error(error, correlation_id="request-123")

    assert status == EXPECTED[code][0]
    assert body == {
        "error": {
            "code": code.value,
            "recovery": EXPECTED[code][1].value,
            "message": ERROR_DEFINITIONS[code].message,
            "correlationId": "request-123",
        }
    }
    assert str(error) == code.value


def test_account_and_identity_messages_do_not_enumerate_users() -> None:
    messages = {
        ERROR_DEFINITIONS[code].message
        for code in (
            ErrorCode.ACCESS_NOT_PROVISIONED,
            ErrorCode.ACCOUNT_DISABLED,
            ErrorCode.IDENTITY_CONFLICT,
        )
    }
    assert messages == {"Access is unavailable. Contact your administrator."}


@pytest.mark.parametrize(
    "code",
    [
        ErrorCode.OAUTH_CANCELLED,
        ErrorCode.OAUTH_PROVIDER_UNAVAILABLE,
        ErrorCode.OAUTH_RESPONSE_INVALID,
        ErrorCode.ACCESS_NOT_PROVISIONED,
        ErrorCode.ACCOUNT_DISABLED,
        ErrorCode.IDENTITY_CONFLICT,
        ErrorCode.CANDIDATE_PROFILE_CONFLICT,
    ],
)
def test_callback_redirect_contains_only_safe_code_and_correlation(code: ErrorCode) -> None:
    location = callback_error_redirect(code, correlation_id="request id/123")
    parsed = urlsplit(location)

    assert parsed.path == "/auth/error"
    assert parse_qs(parsed.query) == {
        "code": [code.value],
        "correlation_id": ["request id/123"],
    }
    assert parsed.fragment == ""


def test_callback_redirect_rejects_non_callback_error_codes() -> None:
    with pytest.raises(ValueError):
        callback_error_redirect(ErrorCode.FORBIDDEN, correlation_id="request-123")
