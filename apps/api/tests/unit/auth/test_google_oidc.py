from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import app.auth.google_oidc as google_oidc
import httpx
import pytest
from app.auth.errors import AuthError, ErrorCode
from app.auth.google_oidc import AuthlibGoogleOIDCAdapter, GoogleClaims, validate_google_claims
from authlib.jose import JoseError, JsonWebKey, JsonWebToken
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

NOW = datetime(2026, 8, 9, 9, 0, tzinfo=UTC)


def valid_claims(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "iss": "https://accounts.google.com",
        "sub": "stable-subject",
        "aud": "client-id",
        "exp": int((NOW + timedelta(minutes=5)).timestamp()),
        "nonce": "expected-nonce",
        "email": "person@example.test",
        "email_verified": True,
        "name": "  Ada   Lovelace  ",
        "picture": "https://images.example.test/ada.png",
    }
    values.update(overrides)
    return values


def test_verified_claims_are_strictly_decoded() -> None:
    claims = validate_google_claims(
        valid_claims(),
        signature_verified=True,
        expected_issuer="https://accounts.google.com",
        expected_audience="client-id",
        expected_nonce="expected-nonce",
        now=NOW,
    )

    assert claims == GoogleClaims(
        issuer="https://accounts.google.com",
        subject="stable-subject",
        email="person@example.test",
        name="Ada Lovelace",
        picture="https://images.example.test/ada.png",
    )


@pytest.mark.parametrize(
    "picture",
    [
        None,
        "",
        "http://images.example.test/person.png",
        "//images.example.test/person.png",
        "https://user:secret@images.example.test/person.png",
        "https://images.example.test/person.png\x00",
        "https://[malformed/person.png",
        "https://images.example.test/" + "x" * 2049,
        42,
    ],
)
def test_unusable_optional_picture_is_ignored(picture: object) -> None:
    claims = validate_google_claims(
        valid_claims(picture=picture),
        signature_verified=True,
        expected_issuer="https://accounts.google.com",
        expected_audience="client-id",
        expected_nonce="expected-nonce",
        now=NOW,
    )
    assert claims.picture is None


def test_legacy_google_issuer_is_accepted_for_the_configured_google_issuer() -> None:
    claims = validate_google_claims(
        valid_claims(iss="accounts.google.com"),
        signature_verified=True,
        expected_issuer="https://accounts.google.com",
        expected_audience="client-id",
        expected_nonce="expected-nonce",
        now=NOW,
    )
    assert claims.issuer == "accounts.google.com"


@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "https://attacker.example"},
        {"aud": "wrong-client"},
        {"exp": int(NOW.timestamp())},
        {"nonce": "wrong"},
        {"sub": ""},
        {"email": ""},
        {"email": "not-an-email"},
        {"email_verified": False},
    ],
)
def test_invalid_claims_fail_closed(overrides: dict[str, object]) -> None:
    with pytest.raises(AuthError) as error:
        validate_google_claims(
            valid_claims(**overrides),
            signature_verified=True,
            expected_issuer="https://accounts.google.com",
            expected_audience="client-id",
            expected_nonce="expected-nonce",
            now=NOW,
        )
    assert error.value.code is ErrorCode.OAUTH_RESPONSE_INVALID


def test_unverified_signature_fails_closed() -> None:
    with pytest.raises(AuthError):
        validate_google_claims(
            valid_claims(),
            signature_verified=False,
            expected_issuer="https://accounts.google.com",
            expected_audience="client-id",
            expected_nonce="expected-nonce",
            now=NOW,
        )


@pytest.mark.parametrize("name", [None, "", "bad\x00name", "x" * 201, 42])
def test_unusable_optional_name_is_ignored(name: object) -> None:
    claims = validate_google_claims(
        valid_claims(name=name),
        signature_verified=True,
        expected_issuer="https://accounts.google.com",
        expected_audience="client-id",
        expected_nonce="expected-nonce",
        now=NOW,
    )
    assert claims.name is None


def test_missing_or_malformed_claims_fail_closed() -> None:
    for payload in ({}, {"iss": object()}):
        with pytest.raises(AuthError):
            validate_google_claims(
                payload,
                signature_verified=True,
                expected_issuer="https://accounts.google.com",
                expected_audience="client-id",
                expected_nonce="expected-nonce",
                now=NOW,
            )


def _adapter(client: httpx.AsyncClient) -> AuthlibGoogleOIDCAdapter:
    return AuthlibGoogleOIDCAdapter(
        client_id="client-id",
        client_secret="test-only",  # noqa: S106
        issuer="https://accounts.google.com",
        redirect_uri="https://app.example/callback",
        http_client=client,
    )


@pytest.mark.asyncio
async def test_authlib_adapter_builds_authorization_and_verifies_signed_token() -> None:
    private_key = rsa.generate_private_key(public_exponent=65_537, key_size=2048)
    key_options = {"kid": "test-key"}
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_jwk = JsonWebKey.import_key(public_pem, key_options).as_dict()
    jwt = JsonWebToken(["RS256"])
    token = jwt.encode(
        {"alg": "RS256", "kid": "test-key"},
        valid_claims(),
        private_pem,
    ).decode()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"id_token": token})
        return httpx.Response(200, json={"keys": [public_jwk]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = _adapter(client)
        location = adapter.authorization_url(
            state="state",
            nonce="expected-nonce",
            pkce_challenge="challenge",
            redirect_uri="https://app.example/callback",
        )
        claims = await adapter.exchange(
            code="code",
            pkce_verifier="verifier",
            expected_nonce_digest=hashlib.sha256(b"expected-nonce").digest(),
            now=NOW,
        )
        with pytest.raises(AuthError) as nonce_error:
            await adapter.exchange(
                code="code",
                pkce_verifier="verifier",
                expected_nonce_digest=hashlib.sha256(b"wrong-nonce").digest(),
                now=NOW,
            )
    assert "code_challenge=challenge" in location
    assert claims.subject == "stable-subject"
    assert nonce_error.value.code is ErrorCode.OAUTH_RESPONSE_INVALID


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["missing", "http", "invalid", "nonce"])
async def test_authlib_adapter_maps_provider_and_invalid_responses(mode: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if mode == "http":
            return httpx.Response(503)
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={} if mode == "missing" else {"id_token": "invalid"})
        return httpx.Response(200, json={"keys": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AuthError) as error:
            await _adapter(client).exchange(
                code="code",
                pkce_verifier="verifier",
                expected_nonce_digest=hashlib.sha256(
                    b"different" if mode == "nonce" else b"expected-nonce"
                ).digest(),
                now=NOW,
            )
    expected = (
        ErrorCode.OAUTH_PROVIDER_UNAVAILABLE if mode == "http" else ErrorCode.OAUTH_RESPONSE_INVALID
    )
    assert error.value.code is expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "reason"),
    [
        ("signature", "signature_or_jwk"),
        ("standard", "standard_claim_validation"),
        ("application", "application_claim_validation"),
        ("malformed", "malformed_provider_response"),
    ],
)
async def test_authlib_adapter_records_safe_invalid_response_stage(
    mode: str,
    reason: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(google_oidc.logger, "disabled", False)
    caplog.set_level("WARNING", logger=google_oidc.logger.name)

    class Claims(dict[str, object]):
        def validate(self, *, now: float, leeway: int) -> None:
            assert now == NOW.timestamp()
            assert leeway == 120
            if mode == "standard":
                raise JoseError("invalid standard claim")

    class TokenDecoder:
        def decode(self, id_token: str, jwks: object) -> Claims:
            del id_token, jwks
            if mode == "signature":
                raise JoseError("invalid signature")
            payload = valid_claims()
            if mode == "application":
                payload["iss"] = "https://attacker.example"
            return Claims(payload)

    if mode == "malformed":

        def invalid_decoder(algorithms: list[str]) -> object:
            del algorithms
            raise ValueError("malformed response")

        monkeypatch.setattr(google_oidc, "JsonWebToken", invalid_decoder)
    else:
        monkeypatch.setattr(google_oidc, "JsonWebToken", lambda algorithms: TokenDecoder())

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"id_token": "signed-token"})
        return httpx.Response(200, json={"keys": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AuthError) as error:
            await _adapter(client).exchange(
                code="code",
                pkce_verifier="verifier",
                expected_nonce_digest=hashlib.sha256(b"expected-nonce").digest(),
                now=NOW,
            )
    assert error.value.code is ErrorCode.OAUTH_RESPONSE_INVALID
    assert f"reason={reason}" in caplog.text


@pytest.mark.asyncio
async def test_authlib_adapter_closes_its_owned_http_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed = False

    class FailingClient:
        def __init__(self, *, timeout: float) -> None:
            assert timeout == 10.0

        async def post(self, url: str, *, data: object) -> httpx.Response:
            del data
            raise httpx.ConnectError("offline", request=httpx.Request("POST", url))

        async def aclose(self) -> None:
            nonlocal closed
            closed = True

    monkeypatch.setattr("app.auth.google_oidc.httpx.AsyncClient", FailingClient)
    adapter = AuthlibGoogleOIDCAdapter(
        client_id="client-id",
        client_secret="test-only",  # noqa: S106
        issuer="https://accounts.google.com",
        redirect_uri="https://app.example/callback",
    )
    with pytest.raises(AuthError) as error:
        await adapter.exchange(
            code="code",
            pkce_verifier="verifier",
            expected_nonce_digest=hashlib.sha256(b"nonce").digest(),
            now=NOW,
        )
    assert error.value.code is ErrorCode.OAUTH_PROVIDER_UNAVAILABLE
    assert closed is True
