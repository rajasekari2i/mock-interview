"""Restrictive response headers for authenticated and authentication routes."""

from __future__ import annotations

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class ProtectedResponseHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault("X-Content-Type-Options", "nosniff")
                headers.setdefault("Referrer-Policy", "no-referrer")
                headers.setdefault("X-Frame-Options", "DENY")
                path = str(scope.get("path", ""))
                if path.startswith("/api/v1/auth") or path.startswith("/api/v1/admin"):
                    headers["Cache-Control"] = "no-store"
                if path.endswith("/auth/logout"):
                    headers["Clear-Site-Data"] = '"cache"'
            await send(message)

        await self.app(scope, receive, send_with_headers)
