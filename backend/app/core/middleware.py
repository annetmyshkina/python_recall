from collections import deque

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.app.core.error_handlers import problem_response

MAX_JSON_BODY_BYTES = 1024 * 1024
BODY_METHODS = {"POST", "PUT", "PATCH"}


class JsonBodyLimitMiddleware:
    """Reject oversized JSON bodies before FastAPI parses them."""

    def __init__(self, app: ASGIApp, max_bytes: int = MAX_JSON_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = problem_response(
            Request(scope),
            status_code=413,
            code="request_too_large",
            title="Request body is too large",
            detail=f"JSON request body must not exceed {self.max_bytes} bytes.",
        )
        await response(scope, receive, send)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in BODY_METHODS:
            await self.app(scope, receive, send)
            return

        headers = dict(scope["headers"])
        content_type = headers.get(b"content-type", b"").split(b";", 1)[0].lower()
        if content_type != b"application/json" and not content_type.endswith(b"+json"):
            await self.app(scope, receive, send)
            return

        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_bytes:
                    await self._reject(scope, receive, send)
                    return
            except ValueError:
                pass

        received = 0
        buffered: deque[Message] = deque()
        while True:
            message = await receive()
            buffered.append(message)
            if message["type"] != "http.request":
                break
            received += len(message.get("body", b""))
            if received > self.max_bytes:
                await self._reject(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        async def replay_receive() -> Message:
            if buffered:
                return buffered.popleft()
            return await receive()

        await self.app(scope, replay_receive, send)
