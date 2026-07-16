"""Bound statement multipart bodies before Starlette spools file parts."""

from __future__ import annotations

import json
import re

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import settings

_PREVIEW_PATH = re.compile(r"^/profiles/[^/]+/imports/preview$")


class _RequestBodyTooLarge(Exception):
    pass


class ImportBodyLimitMiddleware:
    """Reject oversized import requests at the ASGI receive boundary."""

    def __init__(self, app: ASGIApp, max_body_bytes: int | None = None) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._applies(scope):
            await self.app(scope, receive, send)
            return
        limit = self.max_body_bytes or (
            settings.import_max_bytes + settings.import_multipart_overhead_bytes
        )
        content_length = _content_length(scope)
        if content_length is not None and content_length > limit:
            await _send_too_large(send, limit)
            return

        consumed = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal consumed
            message = await receive()
            if message["type"] == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > limit:
                    raise _RequestBodyTooLarge
            return message

        async def tracked_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except _RequestBodyTooLarge:
            if response_started:
                raise
            await _send_too_large(send, limit)

    @staticmethod
    def _applies(scope: Scope) -> bool:
        return (
            scope["type"] == "http"
            and scope.get("method") == "POST"
            and _PREVIEW_PATH.fullmatch(scope.get("path", "")) is not None
        )


def _content_length(scope: Scope) -> int | None:
    for raw_name, raw_value in scope.get("headers", ()):
        if raw_name.lower() == b"content-length":
            try:
                value = int(raw_value)
            except ValueError:
                return None
            return value if value >= 0 else None
    return None


async def _send_too_large(send: Send, limit: int) -> None:
    payload = json.dumps(
        {
            "detail": f"statement request exceeds the configured {limit}-byte limit",
            "code": "request_body_too_large",
            "import_id": None,
            "duplicate_of_import_id": None,
            "status": None,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(payload)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": payload})
