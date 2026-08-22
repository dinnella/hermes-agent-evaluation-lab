#!/usr/bin/env python3
"""Exercise the bounded MCP server without external dependencies."""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import threading
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT / "deploy" / "github-actions" / "mcp" / "server.py"


def rpc(port: int, request_id: int, method: str, params: dict | None = None) -> dict:
    body = json.dumps(
        {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}
    ).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/mcp",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=3) as response:
        return json.load(response)


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        token_path = Path(temp_dir) / "token"
        token_path.write_text("synthetic-test-token", encoding="utf-8")
        os.environ.update(
            {
                "MCP_REPOSITORY": "example/project",
                "MCP_SHA": "0123456789abcdef",
                "MCP_RUN_ID": "42",
                "MCP_AUTH_TOKEN_FILE": str(token_path),
            }
        )
        spec = importlib.util.spec_from_file_location("actions_mcp_server", SERVER_PATH)
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not load MCP server module")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        server = module.ThreadingHTTPServer(("127.0.0.1", 0), module.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        try:
            initialized = rpc(port, 1, "initialize")
            assert initialized["result"]["protocolVersion"] == "2025-06-18"
            listed = rpc(port, 2, "tools/list")
            names = {item["name"] for item in listed["result"]["tools"]}
            assert {"get_workflow_context", "get_repository_metadata"} <= names
            called = rpc(
                port,
                3,
                "tools/call",
                {"name": "get_workflow_context", "arguments": {}},
            )
            content = json.loads(called["result"]["content"][0]["text"])
            assert content["repository"] == "example/project"
            assert content["sha"] == "0123456789abcdef"
            denied = rpc(
                port,
                4,
                "tools/call",
                {"name": "get_workflow_context", "arguments": {"repository": "other/repo"}},
            )
            assert denied["error"]["code"] == -32602
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    print("Validated bounded MCP initialize, discovery, call, and target rejection.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())