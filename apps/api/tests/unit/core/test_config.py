from __future__ import annotations

from typing import Any

import pytest
from app.core.config import AppEnvironment, Settings
from cryptography.fernet import Fernet
from pydantic import ValidationError


def valid_settings(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "app_env": AppEnvironment.TEST,
        "database_url": "postgresql+psycopg://user:password@localhost:5432/mockinterview",
        "google_oidc_client_id": "test-client",
        "google_oidc_client_secret": "test-secret",
        "google_oidc_issuer": "https://accounts.google.com",
        "google_oidc_redirect_uri": "http://localhost:8000/api/v1/auth/google/callback",
        "oauth_transaction_encryption_keys": f"current={Fernet.generate_key().decode()}",
        "oauth_transaction_ttl_seconds": 600,
        "oauth_return_paths": "/,/candidate,/manager,/admin",
        "session_absolute_seconds": 28_800,
        "session_idle_seconds": 7_200,
        "session_cookie_name": "mi_session_test",
        "session_cookie_secure": False,
        "frontend_origins": ["http://localhost:5173"],
        "csrf_allowed_origins": ["http://localhost:5173"],
        "frontend_application_origin": "http://localhost:5173",
        "enable_fake_oidc": True,
    }
    values.update(overrides)
    return values


def test_required_configuration_is_not_optional() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("database_url", "sqlite:///unsafe.db"),
        ("google_oidc_issuer", "http://accounts.google.com"),
        ("google_oidc_redirect_uri", "ftp://api.example.test/callback"),
        ("oauth_transaction_encryption_keys", "current=not-a-fernet-key"),
        ("oauth_transaction_ttl_seconds", 0),
        ("oauth_return_paths", "https://attacker.example/return"),
        ("session_absolute_seconds", 3_600),
        ("session_idle_seconds", 28_801),
        ("frontend_origins", ["*"]),
        ("csrf_allowed_origins", ["https://other.example"]),
        ("frontend_application_origin", "*"),
        ("frontend_application_origin", "https://attacker.example"),
    ],
)
def test_malformed_or_policy_incompatible_configuration_is_rejected(
    field: str, value: object
) -> None:
    with pytest.raises(ValidationError):
        Settings(**valid_settings(**{field: value}))


def test_current_and_previous_pkce_keys_are_parsed_in_rotation_order() -> None:
    current = Fernet.generate_key().decode()
    previous = Fernet.generate_key().decode()

    settings = Settings(
        **valid_settings(
            oauth_transaction_encryption_keys=f"current={current},previous={previous}"
        )
    )

    assert [item.key_id for item in settings.oauth_encryption_keys] == ["current", "previous"]
    assert [item.key for item in settings.oauth_encryption_keys] == [current, previous]
    assert settings.allowed_return_paths == ("/", "/candidate", "/manager", "/admin")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("session_cookie_secure", False),
        ("session_cookie_name", "mi_session"),
        ("enable_fake_oidc", True),
        ("frontend_origins", ["http://localhost:5173"]),
        ("google_oidc_redirect_uri", "http://api.example.test/callback"),
        ("frontend_application_origin", "http://app.example.test"),
    ],
)
def test_production_unsafe_configuration_is_rejected(field: str, value: object) -> None:
    production = valid_settings(
        app_env=AppEnvironment.PRODUCTION,
        database_url="postgresql+psycopg://user:password@db.example.test:5432/mockinterview",
        google_oidc_redirect_uri="https://api.example.test/api/v1/auth/google/callback",
        session_cookie_name="__Host-mi_session",
        session_cookie_secure=True,
        frontend_origins=["https://app.example.test"],
        csrf_allowed_origins=["https://app.example.test"],
        frontend_application_origin="https://app.example.test",
        enable_fake_oidc=False,
    )
    assert Settings(**production).app_env is AppEnvironment.PRODUCTION
    production[field] = value

    with pytest.raises(ValidationError):
        Settings(**production)


def test_duplicate_key_ids_and_return_paths_are_rejected() -> None:
    key_one = Fernet.generate_key().decode()
    key_two = Fernet.generate_key().decode()

    with pytest.raises(ValidationError):
        Settings(
            **valid_settings(
                oauth_transaction_encryption_keys=f"current={key_one},current={key_two}"
            )
        )
    with pytest.raises(ValidationError):
        Settings(**valid_settings(oauth_return_paths="/,/"))


def test_configuration_is_immutable_and_rejects_unknown_fields() -> None:
    settings = Settings(**valid_settings())

    with pytest.raises(ValidationError):
        Settings(**valid_settings(unknown_setting="unsafe"))
    with pytest.raises(ValidationError):
        settings.session_idle_seconds = 1
