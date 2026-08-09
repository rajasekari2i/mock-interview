"""Encrypted, expiring, one-time OAuth transaction persistence."""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.errors import AuthError, ErrorCode
from app.auth.models import OAuthTransaction


@dataclass(frozen=True)
class CreatedOAuthTransaction:
    state: str
    nonce: str
    pkce_challenge: str
    return_path: str


@dataclass(frozen=True)
class ConsumedOAuthTransaction:
    nonce_digest: bytes
    pkce_verifier: str
    return_path: str


def _digest(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def _challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class OAuthTransactionService:
    def __init__(
        self,
        keys: tuple[tuple[str, str], ...],
        *,
        allowed_return_paths: tuple[str, ...],
        ttl_seconds: int = 600,
    ) -> None:
        if not keys:
            raise ValueError("At least one OAuth encryption key is required")
        self._keys = {key_id: Fernet(key.encode("ascii")) for key_id, key in keys}
        self._current_key_id = keys[0][0]
        self._allowed_return_paths = frozenset(allowed_return_paths)
        self._ttl = timedelta(seconds=ttl_seconds)

    async def create(
        self, session: AsyncSession, *, return_path: str, now: datetime
    ) -> CreatedOAuthTransaction:
        if return_path not in self._allowed_return_paths:
            raise ValueError("OAuth return path is not allowlisted")
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        ciphertext = self._keys[self._current_key_id].encrypt(verifier.encode("ascii"))
        session.add(
            OAuthTransaction(
                state_digest=_digest(state),
                nonce_digest=_digest(nonce),
                pkce_verifier_ciphertext=ciphertext,
                encryption_key_id=self._current_key_id,
                return_path=return_path,
                created_at=now,
                expires_at=now + self._ttl,
                consumed_at=None,
            )
        )
        return CreatedOAuthTransaction(
            state=state,
            nonce=nonce,
            pkce_challenge=_challenge(verifier),
            return_path=return_path,
        )

    async def consume(
        self, session: AsyncSession, *, state: str, now: datetime
    ) -> ConsumedOAuthTransaction:
        transaction = await session.scalar(
            select(OAuthTransaction)
            .where(OAuthTransaction.state_digest == _digest(state))
            .with_for_update()
        )
        if (
            transaction is None
            or transaction.consumed_at is not None
            or now >= transaction.expires_at
        ):
            raise AuthError(ErrorCode.OAUTH_RESPONSE_INVALID)
        fernet = self._keys.get(transaction.encryption_key_id)
        if fernet is None:
            raise AuthError(ErrorCode.OAUTH_RESPONSE_INVALID)
        try:
            verifier = fernet.decrypt(transaction.pkce_verifier_ciphertext).decode("ascii")
        except (InvalidToken, UnicodeDecodeError) as error:
            raise AuthError(ErrorCode.OAUTH_RESPONSE_INVALID) from error
        transaction.consumed_at = now
        return ConsumedOAuthTransaction(
            nonce_digest=transaction.nonce_digest,
            pkce_verifier=verifier,
            return_path=transaction.return_path,
        )
