"""Strict environment configuration for authentication infrastructure."""

from __future__ import annotations

from enum import StrEnum
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class OAuthEncryptionKey(BaseModel):
    """One validated key in newest-to-oldest rotation order."""

    model_config = ConfigDict(frozen=True)

    key_id: str
    key: str


def _split_keys(value: str) -> tuple[OAuthEncryptionKey, ...]:
    parsed: list[OAuthEncryptionKey] = []
    seen_ids: set[str] = set()
    for raw_item in value.split(","):
        key_id, separator, key = raw_item.strip().partition("=")
        if not separator or not key_id or not key or key_id in seen_ids:
            raise ValueError("PKCE encryption keys require unique non-empty key IDs")
        Fernet(key.encode("ascii"))
        seen_ids.add(key_id)
        parsed.append(OAuthEncryptionKey(key_id=key_id, key=key))
    return tuple(parsed)


def _is_origin(value: str) -> bool:
    parsed = urlsplit(value)
    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.netloc)
        and parsed.path in {"", "/"}
        and not parsed.query
        and not parsed.fragment
        and value != "*"
    )


class Settings(BaseSettings):
    """Immutable, fail-closed application settings."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=None,
        extra="forbid",
        frozen=True,
    )

    app_env: AppEnvironment
    database_url: str = Field(min_length=1)
    google_oidc_client_id: str = Field(min_length=1)
    google_oidc_client_secret: str = Field(min_length=1)
    google_oidc_issuer: str = Field(min_length=1)
    google_oidc_redirect_uri: str = Field(min_length=1)
    oauth_transaction_encryption_keys: str = Field(min_length=1)
    oauth_transaction_ttl_seconds: int = Field(ge=1, le=900)
    oauth_return_paths: str = Field(min_length=1)
    session_absolute_seconds: int
    session_idle_seconds: int
    session_cookie_name: str = Field(min_length=1)
    session_cookie_secure: bool
    frontend_origins: list[str] = Field(min_length=1)
    csrf_allowed_origins: list[str] = Field(min_length=1)
    frontend_application_origin: str = Field(min_length=1)
    enable_fake_oidc: bool

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith(("postgresql+psycopg://", "postgresql+psycopg_async://")):
            raise ValueError("DATABASE_URL must select PostgreSQL through psycopg")
        return value

    @field_validator("google_oidc_issuer")
    @classmethod
    def validate_issuer(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
            raise ValueError("Google OIDC issuer must be an HTTPS origin")
        return value.rstrip("/")

    @field_validator("google_oidc_redirect_uri")
    @classmethod
    def validate_redirect_uri(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.fragment:
            raise ValueError("Google OIDC redirect URI must be an absolute HTTP(S) URL")
        return value

    @field_validator("oauth_transaction_encryption_keys")
    @classmethod
    def validate_encryption_keys(cls, value: str) -> str:
        _split_keys(value)
        return value

    @field_validator("oauth_return_paths")
    @classmethod
    def validate_return_paths(cls, value: str) -> str:
        paths = tuple(item.strip() for item in value.split(","))
        if (
            not paths
            or len(paths) != len(set(paths))
            or any(not path.startswith("/") or path.startswith("//") for path in paths)
        ):
            raise ValueError("OAuth return paths must be unique relative paths")
        return value

    @field_validator("frontend_origins", "csrf_allowed_origins")
    @classmethod
    def validate_origins(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)) or any(not _is_origin(value) for value in values):
            raise ValueError("Origins must be unique explicit HTTP(S) origins")
        return values

    @field_validator("frontend_application_origin")
    @classmethod
    def validate_application_origin(cls, value: str) -> str:
        if not _is_origin(value):
            raise ValueError("Frontend application origin must be one explicit HTTP(S) origin")
        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_security_policy(self) -> Settings:
        if self.session_absolute_seconds != 28_800 or self.session_idle_seconds != 7_200:
            raise ValueError("Session policy must remain 8 hours absolute and 2 hours idle")
        if set(self.csrf_allowed_origins) != set(self.frontend_origins):
            raise ValueError("CSRF and credentialed frontend origin allowlists must match")
        if self.frontend_application_origin not in self.frontend_origins:
            raise ValueError("Frontend application origin must be in the frontend allowlist")
        if self.app_env is AppEnvironment.PRODUCTION:
            redirect = urlsplit(self.google_oidc_redirect_uri)
            if (
                not self.session_cookie_secure
                or self.session_cookie_name != "__Host-mi_session"
                or self.enable_fake_oidc
                or redirect.scheme != "https"
                or any(urlsplit(origin).scheme != "https" for origin in self.frontend_origins)
                or urlsplit(self.frontend_application_origin).scheme != "https"
            ):
                raise ValueError("Production authentication configuration is unsafe")
        return self

    @property
    def oauth_encryption_keys(self) -> tuple[OAuthEncryptionKey, ...]:
        return _split_keys(self.oauth_transaction_encryption_keys)

    @property
    def allowed_return_paths(self) -> tuple[str, ...]:
        return tuple(item.strip() for item in self.oauth_return_paths.split(","))
