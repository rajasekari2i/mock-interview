"""Cookie and CSRF policy primitives."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import TypedDict

from app.auth.errors import AuthError, ErrorCode


class CookieOptions(TypedDict):
    secure: bool
    httponly: bool
    samesite: str
    path: str


@dataclass(frozen=True)
class SessionCookiePolicy:
    name: str
    options: CookieOptions

    @classmethod
    def production(cls) -> SessionCookiePolicy:
        return cls(
            name="__Host-mi_session",
            options={"secure": True, "httponly": True, "samesite": "lax", "path": "/"},
        )

    @classmethod
    def development(cls, name: str) -> SessionCookiePolicy:
        if name.startswith("__Host-"):
            raise ValueError("Insecure development cookies cannot use the __Host- prefix")
        return cls(
            name=name,
            options={"secure": False, "httponly": True, "samesite": "lax", "path": "/"},
        )


class CsrfPolicy:
    def __init__(self, allowed_origins: tuple[str, ...]) -> None:
        self._allowed_origins = frozenset(allowed_origins)

    def validate(
        self,
        *,
        origin: str,
        cookie_token: str,
        header_token: str,
        expected_digest: bytes,
    ) -> None:
        presented_digest = hashlib.sha256(header_token.encode("utf-8")).digest()
        if (
            origin not in self._allowed_origins
            or not cookie_token
            or not header_token
            or not hmac.compare_digest(cookie_token, header_token)
            or not hmac.compare_digest(presented_digest, expected_digest)
        ):
            raise AuthError(ErrorCode.CSRF_DENIED)
