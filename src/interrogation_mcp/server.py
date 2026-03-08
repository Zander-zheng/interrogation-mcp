from __future__ import annotations

import json

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from interrogation_mcp.auth import ApiKeyMiddleware
from interrogation_mcp.client import InterrogationClient
from interrogation_mcp.config import settings

# ---------------------------------------------------------------------------
# Tool description
# ---------------------------------------------------------------------------

INTERROGATE_DESCRIPTION = """
DEFINITION: Subjects an inchoate ontological hunch to Affordance-Abundance-Agency
pressure through multi-round co-constitutive crystallization. Call WITHOUT thread_id
to start a new session; call WITH thread_id to continue an existing one. The tool
manages a 4-phase protocol (Hunch Reception → Structural Reconnaissance → 3A Pressure
Deployment → Constellation Synthesis) across multiple calls, returning the consultant's
response each time until the final <3a_enriched_constellation> artifact is produced.

WHEN TO USE:
- User has a directional intuition / hunch they want crystallized into precise coordinates
- User wants ontological clarity on something they can feel but can't fully articulate
- Continuing a multi-round interrogation session (pass thread_id + user's reply)

WHEN NOT TO USE:
- User wants a quick answer or simple brainstorm (this is a structured multi-phase process)
- Input is already well-articulated analysis (the tool is for inchoate hunches needing crystallization)
- User needs factual lookup or summarization (this produces ontological coordinates, not information retrieval)

DISTINCT EDGE: Unlike generic brainstorming or Q&A, this deploys structured triadic
pressure (Affordance/Abundance/Agency) through a governed 4-phase protocol that
simultaneously crystallizes WHAT question the hunch is really asking and WHAT the
discriminated answer looks like — producing coordinates neither party could access alone.
Each call advances the conversation; is_complete signals when the final artifact is ready.

INPUT SCHEMA:
  message (str, required): The hunch (first call) or user's reply to the consultant (subsequent calls)
  thread_id (str, optional): Omit for a new session. Include to continue an existing session.

OUTPUT SCHEMA:
{
  "thread_id": "string — pass this back on every subsequent call",
  "ai_response": "string — the consultant's response (probe, ratification request, or final synthesis)",
  "is_complete": "boolean — false while conversation continues, true when final artifact is produced",
  "artifact": "string (only when is_complete=true) — the <3a_enriched_constellation> with Overarching Pivotal Question and Insight Constellation axes"
}

SAMPLE OUTPUT (first call — Phase 1):
{
  "thread_id": "a1b2c3d4-...",
  "ai_response": "**Phase 1: Hunch Reception & Domain Orientation**\\n\\nI register your hunch as reaching toward...[domain analysis, 2-3 preliminary pressure-points, ratification request]",
  "is_complete": false
}

SAMPLE OUTPUT (final call — Phase 4 complete):
{
  "thread_id": "a1b2c3d4-...",
  "ai_response": "**Phase 4: Constellation Synthesis**\\n\\n<3a_enriched_constellation>...",
  "is_complete": true,
  "artifact": "<3a_enriched_constellation>\\n\\n## Overarching Pivotal Question\\n[...]\\n\\n## Insight Constellation\\n\\n### [Axis 1]\\n[...]\\n\\n### [Axis 2]\\n[...]\\n\\n</3a_enriched_constellation>"
}
""".strip()

# ---------------------------------------------------------------------------
# MCP server + tools
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "3a-interrogation",
    host="0.0.0.0",
    port=8000,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "interrogation-mcp-production.up.railway.app",
            "localhost:8000",
        ],
    ),
)
interrogation_client = InterrogationClient(settings.deployment_url, settings.langsmith_api_key)


@mcp.tool(description=INTERROGATE_DESCRIPTION)
async def interrogate(message: str, thread_id: str | None = None) -> str:
    result = await interrogation_client.interrogate(message, thread_id)
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# ASGI app: dual transport (SSE + Streamable HTTP), wrapped with auth
# ---------------------------------------------------------------------------

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


def create_app():
    """Build the ASGI app with both SSE and Streamable HTTP transports.

    Endpoints:
        /health       — healthcheck (no auth)
        /sse          — SSE transport (Cursor, Claude Code, Claude Desktop)
        /messages/    — SSE message endpoint (session-bound, no auth needed)
        /mcp          — Streamable HTTP transport (ChatGPT, newer clients)
    """
    # streamable_http_app() returns a Starlette with lifespan management.
    # Use it as the base app and add SSE + health routes to it.
    app = mcp.streamable_http_app()

    # Get the SSE app and mount its routes into the main app
    sse = mcp.sse_app()
    for route in sse.routes:
        app.routes.append(route)

    # Add health endpoint
    async def health(request: Request):
        return JSONResponse({"status": "ok"})

    app.routes.insert(0, Route("/health", health))

    if settings.mcp_api_key:
        return ApiKeyMiddleware(app, settings.mcp_api_key)
    return app


if __name__ == "__main__":
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)
