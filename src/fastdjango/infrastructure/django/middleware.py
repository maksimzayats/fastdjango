from asgiref.sync import ThreadSensitiveContext, sync_to_async
from django.db import close_old_connections
from starlette.types import ASGIApp, Receive, Scope, Send


class DjangoDatabaseConnectionMiddleware:
    """Give FastAPI connections Django-like database connection boundaries.

    FastAPI does not run through Django's request handler, so Django's database
    cleanup signals are not sent for HTTP or WebSocket routes. The
    thread-sensitive context matches Django's ASGI handler and prevents
    thread-sensitive ORM work from falling back to asgiref's process-wide
    single-thread executor.
    """

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"}:
            await self._app(scope, receive, send)
            return

        async with ThreadSensitiveContext():  # type: ignore[no-untyped-call]
            await sync_to_async(close_old_connections, thread_sensitive=True)()
            try:
                await self._app(scope, receive, send)
            finally:
                await sync_to_async(close_old_connections, thread_sensitive=True)()
