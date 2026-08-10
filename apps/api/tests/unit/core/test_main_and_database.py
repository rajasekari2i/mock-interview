from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import cast

import httpx
import pytest
from app.core.database import get_session
from app.main import build_app, create_app
from fastapi import FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncSession


class _Database:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncSession]:
        yield self.session


@pytest.mark.asyncio
async def test_health_and_generic_request_middleware_path() -> None:
    transport = httpx.ASGITransport(app=create_app(testing=True))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.json() == {"status": "ok"}
    assert response.headers["x-frame-options"] == "DENY"


@pytest.mark.asyncio
async def test_get_session_yields_database_transaction(db_session: AsyncSession) -> None:
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(database=_Database(db_session)))
    )
    dependency = get_session(cast(Request, request))
    assert await anext(dependency) is db_session
    await dependency.aclose()


def test_build_app_loads_settings_and_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = object()
    expected = FastAPI()
    monkeypatch.setattr("app.main.Settings", lambda: settings)
    monkeypatch.setattr("app.main.create_app", lambda *, settings: expected)
    assert build_app() is expected
