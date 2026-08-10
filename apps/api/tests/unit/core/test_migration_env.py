from __future__ import annotations

import runpy
from contextlib import nullcontext
from pathlib import Path

import alembic
from pytest import MonkeyPatch


class _FakeConfig:
    config_file_name = None
    config_ini_section = "alembic"

    def __init__(self, fallback_url: str) -> None:
        self.fallback_url = fallback_url

    def get_main_option(self, name: str) -> str:
        assert name == "sqlalchemy.url"
        return self.fallback_url

    def get_section(self, name: str, default: object) -> dict[str, str]:
        del name, default
        return {"sqlalchemy.url": self.fallback_url}


class _FakeContext:
    def __init__(self, fallback_url: str) -> None:
        self.config = _FakeConfig(fallback_url)
        self.configured_url = ""

    @staticmethod
    def is_offline_mode() -> bool:
        return True

    def configure(self, **values: object) -> None:
        self.configured_url = str(values["url"])

    @staticmethod
    def begin_transaction() -> object:
        return nullcontext()

    @staticmethod
    def run_migrations() -> None:
        return None


def _execute_env(monkeypatch: MonkeyPatch, *, override: str | None) -> str:
    fallback = "postgresql+psycopg://fallback/test"
    fake_context = _FakeContext(fallback)
    monkeypatch.setattr(alembic, "context", fake_context)
    if override is None:
        monkeypatch.delenv("MOCKINTERVIEW_MIGRATION_DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("MOCKINTERVIEW_MIGRATION_DATABASE_URL", override)
    runpy.run_path(Path("apps/api/migrations/env.py"))
    return fake_context.configured_url


def test_explicit_migration_url_overrides_checked_in_fallback(monkeypatch: MonkeyPatch) -> None:
    override = "postgresql+psycopg://isolated/feature_test"
    assert _execute_env(monkeypatch, override=override) == override


def test_checked_in_url_remains_the_fallback(monkeypatch: MonkeyPatch) -> None:
    assert _execute_env(monkeypatch, override=None) == "postgresql+psycopg://fallback/test"
