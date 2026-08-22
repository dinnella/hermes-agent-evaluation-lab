"""Source-aware egress policy and Copilot credential injection for mitmproxy."""

from __future__ import annotations

import json
import os
from pathlib import Path

from mitmproxy import http


HERMES_IP = os.environ["GATEWAY_HERMES_IP"]
MCP_IP = os.environ["GATEWAY_MCP_IP"]
SENTINEL = os.environ["GATEWAY_SENTINEL"]
COPILOT_TOKEN = Path(os.environ["COPILOT_TOKEN_FILE"]).read_text(encoding="utf-8").strip()
ALLOWED_MODELS = frozenset(
    value.strip()
    for value in os.environ.get("GATEWAY_ALLOWED_MODELS", "gpt-5.4").split(",")
    if value.strip()
)
COPILOT_PATHS = frozenset({"/chat/completions", "/models", "/responses"})


def deny(flow: http.HTTPFlow, status: int, reason: str) -> None:
    flow.response = http.Response.make(
        status,
        json.dumps({"error": reason}, separators=(",", ":")),
        {"Content-Type": "application/json", "Cache-Control": "no-store"},
    )


def request(flow: http.HTTPFlow) -> None:
    peer = flow.client_conn.peername
    source_ip = peer[0] if peer else ""
    host = flow.request.pretty_host.lower().rstrip(".")
    path = flow.request.path.split("?", 1)[0].rstrip("/") or "/"

    if source_ip == HERMES_IP:
        if host != "api.githubcopilot.com" or path not in COPILOT_PATHS:
            deny(flow, 403, "hermes_destination_not_allowed")
            return
        if flow.request.headers.get("Authorization") != f"Bearer {SENTINEL}":
            deny(flow, 401, "invalid_gateway_sentinel")
            return
        if flow.request.raw_content:
            try:
                model = json.loads(flow.request.raw_content).get("model")
            except (json.JSONDecodeError, AttributeError):
                deny(flow, 400, "invalid_json")
                return
            if model is not None and str(model) not in ALLOWED_MODELS:
                deny(flow, 403, "model_not_allowed")
                return
        flow.request.headers["Authorization"] = f"Bearer {COPILOT_TOKEN}"
        flow.request.headers.setdefault("Copilot-Integration-Id", "vscode-chat")
        flow.request.headers.setdefault("Editor-Version", "vscode/1.95.0")
        flow.request.headers.setdefault("Openai-Intent", "conversation-panel")
        flow.request.headers.setdefault("x-initiator", "user")
        return

    if source_ip == MCP_IP:
        if host != "api.github.com" or not path.startswith("/repos/"):
            deny(flow, 403, "mcp_destination_not_allowed")
        return

    deny(flow, 403, "source_not_allowed")


def responseheaders(flow: http.HTTPFlow) -> None:
    # Copilot Responses uses SSE. Stream without buffering model output or
    # credentials into an in-memory completed-flow body.
    peer = flow.client_conn.peername
    if peer and peer[0] == HERMES_IP:
        flow.response.stream = True