from __future__ import annotations

import json


class ApiKeyMiddleware:
    """Pure ASGI middleware — does NOT buffer responses, safe for SSE."""

    def __init__(self, app, api_key: str) -> None:
        self.app = app
        self.api_key = api_key

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        # /health is public; /messages/ is session-bound (session_id is unguessable)
        # and MCP clients don't forward the API key on POST requests after SSE auth.
        # /mcp is the Streamable HTTP transport — ChatGPT and newer clients POST here
        # without auth headers; session security is handled by Mcp-Session-Id header.
        if path == "/health" or path.startswith("/messages") or path.startswith("/mcp"):
            await self.app(scope, receive, send)
            return

        # Extract API key from headers or query string
        headers = dict(scope.get("headers", []))
        key = headers.get(b"x-api-key", b"").decode()

        if not key:
            qs = scope.get("query_string", b"").decode()
            for param in qs.split("&"):
                if param.startswith("x-api-key="):
                    key = param.split("=", 1)[1]
                    break

        if key != self.api_key:
            body = json.dumps({"error": "Invalid or missing API key"}).encode()
            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"content-length", str(len(body)).encode()],
                ],
            })
            await send({"type": "http.response.body", "body": body})
            return

        await self.app(scope, receive, send)
