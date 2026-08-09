"""Delete expired transient OAuth state and aged terminal session rows."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime, timedelta

from app.auth.models import AuthenticationSession, OAuthTransaction
from app.core.config import Settings
from app.core.database import Database
from sqlalchemy import delete, or_
from sqlalchemy.ext.asyncio import AsyncSession


async def cleanup_auth_state(
    session: AsyncSession, *, now: datetime, session_retention_days: int = 30
) -> tuple[int, int]:
    oauth_result = await session.execute(
        delete(OAuthTransaction).where(
            or_(OAuthTransaction.expires_at < now, OAuthTransaction.consumed_at.is_not(None))
        )
    )
    cutoff = now - timedelta(days=session_retention_days)
    session_result = await session.execute(
        delete(AuthenticationSession).where(
            AuthenticationSession.updated_at < cutoff,
            or_(
                AuthenticationSession.revoked_at.is_not(None),
                AuthenticationSession.absolute_expires_at < now,
            ),
        )
    )
    return oauth_result.rowcount, session_result.rowcount


async def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-retention-days", type=int, default=30)
    arguments = parser.parse_args()
    database = Database(Settings())  # type: ignore[call-arg]
    try:
        async with database.transaction() as session:
            removed = await cleanup_auth_state(
                session,
                now=datetime.now(UTC),
                session_retention_days=arguments.session_retention_days,
            )
        print(f"oauth_transactions={removed[0]} authentication_sessions={removed[1]}")
    finally:
        await database.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
