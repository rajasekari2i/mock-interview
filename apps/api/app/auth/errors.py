"""Stable, non-enumerating authentication error contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TypedDict
from urllib.parse import urlencode


class RecoveryAction(StrEnum):
    SIGN_IN_AGAIN = "SIGN_IN_AGAIN"
    CONTACT_ADMIN = "CONTACT_ADMIN"
    RETRY = "RETRY"
    GO_TO_ROLE_HOME = "GO_TO_ROLE_HOME"


class ErrorCode(StrEnum):
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    SESSION_REVOKED = "SESSION_REVOKED"
    ACCESS_NOT_PROVISIONED = "ACCESS_NOT_PROVISIONED"
    ACCOUNT_DISABLED = "ACCOUNT_DISABLED"
    OAUTH_CANCELLED = "OAUTH_CANCELLED"
    OAUTH_PROVIDER_UNAVAILABLE = "OAUTH_PROVIDER_UNAVAILABLE"
    OAUTH_RESPONSE_INVALID = "OAUTH_RESPONSE_INVALID"
    FORBIDDEN = "FORBIDDEN"
    CSRF_DENIED = "CSRF_DENIED"
    IDENTITY_CONFLICT = "IDENTITY_CONFLICT"
    CANDIDATE_PROFILE_CONFLICT = "CANDIDATE_PROFILE_CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"


@dataclass(frozen=True)
class ErrorDefinition:
    http_status: int
    recovery: RecoveryAction
    message: str


_UNAVAILABLE = "Access is unavailable. Contact your administrator."

ERROR_DEFINITIONS: dict[ErrorCode, ErrorDefinition] = {
    ErrorCode.AUTHENTICATION_REQUIRED: ErrorDefinition(
        401, RecoveryAction.SIGN_IN_AGAIN, "Sign in to continue."
    ),
    ErrorCode.SESSION_EXPIRED: ErrorDefinition(
        401, RecoveryAction.SIGN_IN_AGAIN, "Your session ended. Sign in again."
    ),
    ErrorCode.SESSION_REVOKED: ErrorDefinition(
        401, RecoveryAction.SIGN_IN_AGAIN, "Your session ended. Sign in again."
    ),
    ErrorCode.ACCESS_NOT_PROVISIONED: ErrorDefinition(
        403, RecoveryAction.CONTACT_ADMIN, _UNAVAILABLE
    ),
    ErrorCode.ACCOUNT_DISABLED: ErrorDefinition(403, RecoveryAction.CONTACT_ADMIN, _UNAVAILABLE),
    ErrorCode.OAUTH_CANCELLED: ErrorDefinition(
        400, RecoveryAction.RETRY, "Google sign-in was not completed. Try again."
    ),
    ErrorCode.OAUTH_PROVIDER_UNAVAILABLE: ErrorDefinition(
        503, RecoveryAction.RETRY, "Google sign-in is temporarily unavailable. Try again."
    ),
    ErrorCode.OAUTH_RESPONSE_INVALID: ErrorDefinition(
        400, RecoveryAction.RETRY, "Google sign-in could not be verified. Try again."
    ),
    ErrorCode.FORBIDDEN: ErrorDefinition(
        403, RecoveryAction.GO_TO_ROLE_HOME, "This action is not available for your role."
    ),
    ErrorCode.CSRF_DENIED: ErrorDefinition(
        403, RecoveryAction.RETRY, "The request could not be verified. Refresh and try again."
    ),
    ErrorCode.IDENTITY_CONFLICT: ErrorDefinition(409, RecoveryAction.CONTACT_ADMIN, _UNAVAILABLE),
    ErrorCode.CANDIDATE_PROFILE_CONFLICT: ErrorDefinition(
        409, RecoveryAction.CONTACT_ADMIN, "Candidate access requires administrator review."
    ),
    ErrorCode.VALIDATION_ERROR: ErrorDefinition(
        400, RecoveryAction.RETRY, "Check the request and try again."
    ),
    ErrorCode.RESOURCE_NOT_FOUND: ErrorDefinition(
        404, RecoveryAction.GO_TO_ROLE_HOME, "The requested resource is unavailable."
    ),
}


class ErrorBody(TypedDict):
    code: str
    recovery: str
    message: str
    correlationId: str


class ErrorEnvelope(TypedDict):
    error: ErrorBody


class AuthError(Exception):
    def __init__(self, code: ErrorCode) -> None:
        super().__init__(code.value)
        self.code = code


def encode_error(error: AuthError, *, correlation_id: str) -> tuple[int, ErrorEnvelope]:
    definition = ERROR_DEFINITIONS[error.code]
    return (
        definition.http_status,
        {
            "error": {
                "code": error.code.value,
                "recovery": definition.recovery.value,
                "message": definition.message,
                "correlationId": correlation_id,
            }
        },
    )


_CALLBACK_CODES = frozenset(
    {
        ErrorCode.OAUTH_CANCELLED,
        ErrorCode.OAUTH_PROVIDER_UNAVAILABLE,
        ErrorCode.OAUTH_RESPONSE_INVALID,
        ErrorCode.ACCESS_NOT_PROVISIONED,
        ErrorCode.ACCOUNT_DISABLED,
        ErrorCode.IDENTITY_CONFLICT,
        ErrorCode.CANDIDATE_PROFILE_CONFLICT,
    }
)


def callback_error_redirect(code: ErrorCode, *, correlation_id: str) -> str:
    if code not in _CALLBACK_CODES:
        raise ValueError("Error code is not valid for an OAuth callback redirect")
    query = urlencode({"code": code.value, "correlation_id": correlation_id})
    return f"/auth/error?{query}"
