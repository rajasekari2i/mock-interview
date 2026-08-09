"""Narrow Google OIDC boundary with strict post-verification claim decoding."""

from __future__ import annotations

import hashlib
import logging
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, cast
from urllib.parse import urlencode

import httpx
from authlib.jose import JoseError, JsonWebToken  # type: ignore[import-untyped]

from app.auth.errors import AuthError, ErrorCode
from app.auth.identifiers import display_name_from_claim, normalize_verified_email

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GoogleClaims:
    issuer: str
    subject: str
    email: str
    name: str | None = None


class GoogleOIDCProvider(Protocol):
    def authorization_url(
        self, *, state: str, nonce: str, pkce_challenge: str, redirect_uri: str
    ) -> str: ...

    async def exchange(
        self, *, code: str, pkce_verifier: str, expected_nonce_digest: bytes, now: datetime
    ) -> GoogleClaims: ...


def validate_google_claims(
    payload: Mapping[str, object],
    *,
    signature_verified: bool,
    expected_issuer: str,
    expected_audience: str,
    expected_nonce: str,
    now: datetime,
) -> GoogleClaims:
    try:
        issuer = payload["iss"]
        subject = payload["sub"]
        audience = payload["aud"]
        expiry = payload["exp"]
        nonce = payload["nonce"]
        email = payload["email"]
        verified = payload["email_verified"]
        name = payload.get("name")
        issuer_matches = issuer == expected_issuer or (
            expected_issuer == "https://accounts.google.com"
            and issuer == "accounts.google.com"
        )
        audience_matches = audience == expected_audience or (
            isinstance(audience, list) and expected_audience in audience
        )
        valid = (
            signature_verified
            and isinstance(issuer, str)
            and issuer_matches
            and isinstance(subject, str)
            and bool(subject)
            and audience_matches
            and isinstance(expiry, int | float)
            and expiry > now.timestamp()
            and isinstance(nonce, str)
            and secrets.compare_digest(nonce, expected_nonce)
            and isinstance(email, str)
            and bool(email)
            and verified is True
        )
    except (KeyError, TypeError):
        valid = False
    if not valid:
        raise AuthError(ErrorCode.OAUTH_RESPONSE_INVALID)
    try:
        normalized_email, _, local_part = normalize_verified_email(cast(str, email))
    except ValueError as error:
        raise AuthError(ErrorCode.OAUTH_RESPONSE_INVALID) from error
    normalized_name = display_name_from_claim(name, fallback="") or None
    return GoogleClaims(
        issuer=cast(str, issuer),
        subject=cast(str, subject),
        email=normalized_email,
        name=normalized_name,
    )


@dataclass(frozen=True)
class GoogleAuthorizationEndpoint:
    client_id: str
    authorization_endpoint: str = "https://accounts.google.com/o/oauth2/v2/auth"

    def build_url(
        self,
        *,
        state: str,
        nonce: str,
        pkce_challenge: str,
        redirect_uri: str,
    ) -> str:
        query = urlencode(
            {
                "client_id": self.client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "nonce": nonce,
                "code_challenge": pkce_challenge,
                "code_challenge_method": "S256",
            }
        )
        return f"{self.authorization_endpoint}?{query}"


class AuthlibGoogleOIDCAdapter:
    """Backend-only Authlib verifier; provider tokens never leave this boundary."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        issuer: str,
        redirect_uri: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.client_id = client_id
        self._client_secret = client_secret
        self.issuer = issuer
        self.redirect_uri = redirect_uri
        self._http_client = http_client
        self._authorization = GoogleAuthorizationEndpoint(client_id)

    def authorization_url(
        self, *, state: str, nonce: str, pkce_challenge: str, redirect_uri: str
    ) -> str:
        return self._authorization.build_url(
            state=state,
            nonce=nonce,
            pkce_challenge=pkce_challenge,
            redirect_uri=redirect_uri,
        )

    async def exchange(
        self, *, code: str, pkce_verifier: str, expected_nonce_digest: bytes, now: datetime
    ) -> GoogleClaims:
        owns_client = self._http_client is None
        client = self._http_client or httpx.AsyncClient(timeout=10.0)
        try:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                    "code_verifier": pkce_verifier,
                },
            )
            token_response.raise_for_status()
            token_payload = token_response.json()
            id_token = token_payload.get("id_token")
            if not isinstance(id_token, str):
                logger.warning("google_oidc_rejected reason=missing_id_token")
                raise AuthError(ErrorCode.OAUTH_RESPONSE_INVALID)
            jwks_response = await client.get("https://www.googleapis.com/oauth2/v3/certs")
            jwks_response.raise_for_status()
            jwt = JsonWebToken(["RS256"])
            try:
                claims = jwt.decode(id_token, jwks_response.json())
            except JoseError as error:
                logger.warning("google_oidc_rejected reason=signature_or_jwk")
                raise AuthError(ErrorCode.OAUTH_RESPONSE_INVALID) from error
            try:
                claims.validate(now=now.timestamp())
            except JoseError as error:
                logger.warning("google_oidc_rejected reason=standard_claim_validation")
                raise AuthError(ErrorCode.OAUTH_RESPONSE_INVALID) from error
            nonce = claims.get("nonce")
            if not isinstance(nonce, str) or not secrets.compare_digest(
                hashlib.sha256(nonce.encode()).digest(), expected_nonce_digest
            ):
                logger.warning("google_oidc_rejected reason=nonce")
                raise AuthError(ErrorCode.OAUTH_RESPONSE_INVALID)
            try:
                return validate_google_claims(
                    claims,
                    signature_verified=True,
                    expected_issuer=self.issuer,
                    expected_audience=self.client_id,
                    expected_nonce=nonce,
                    now=now,
                )
            except AuthError:
                logger.warning("google_oidc_rejected reason=application_claim_validation")
                raise
        except AuthError:
            raise
        except httpx.HTTPError as error:
            raise AuthError(ErrorCode.OAUTH_PROVIDER_UNAVAILABLE) from error
        except (TypeError, ValueError) as error:
            logger.warning("google_oidc_rejected reason=malformed_provider_response")
            raise AuthError(ErrorCode.OAUTH_RESPONSE_INVALID) from error
        finally:
            if owns_client:
                await client.aclose()
