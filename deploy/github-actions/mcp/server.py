#!/usr/bin/env python3
"""Minimal read-only GitHub MCP server for the Actions smoke test."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


MAX_BODY_BYTES = 1_000_000
PROTOCOL_VERSION = "2025-06-18"
REPOSITORY = os.environ["MCP_REPOSITORY"]
COMMIT_SHA = os.environ["MCP_SHA"]
PULL_NUMBER = os.environ.get("MCP_PULL_NUMBER", "").strip()
TOKEN = Path(os.environ["MCP_AUTH_TOKEN_FILE"]).read_text(encoding="utf-8").strip()


def tool(name: str, description: str) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    }


TOOLS = [
    tool("get_workflow_context", "Return the fixed repository, commit, actor, event, and run identity for this job."),
    tool("get_repository_metadata", "Return bounded metadata for the workflow repository."),
    tool("get_commit_metadata", "Return bounded metadata and changed-file summaries for the fixed workflow commit."),
    tool("get_check_runs", "Return bounded check-run status for the fixed workflow commit."),
]
if PULL_NUMBER:
    TOOLS.extend(
        [
            tool("get_pull_request", "Return bounded metadata for the pull request fixed by the workflow input."),
            tool("get_pull_request_files", "Return at most 100 changed-file summaries for the fixed pull request."),
        ]
    )


def github_get(path: str) -> Any:
    request = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {TOKEN}",
            "User-Agent": "hermes-actions-bounded-mcp/1",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def workflow_context() -> dict[str, str]:
    return {
        "repository": REPOSITORY,
        "sha": COMMIT_SHA,
        "pull_number": PULL_NUMBER,
        "actor": os.environ.get("MCP_ACTOR", ""),
        "event_name": os.environ.get("MCP_EVENT_NAME", ""),
        "run_id": os.environ.get("MCP_RUN_ID", ""),
        "run_attempt": os.environ.get("MCP_RUN_ATTEMPT", ""),
    }


def call_tool(name: str, arguments: Any) -> Any:
    if arguments not in ({}, None):
        raise ValueError("This tool accepts no arguments; its target is fixed by workflow context")

    quoted_repo = "/".join(urllib.parse.quote(part, safe="") for part in REPOSITORY.split("/"))
    if name == "get_workflow_context":
        return workflow_context()
    if name == "get_repository_metadata":
        data = github_get(f"/repos/{quoted_repo}")
        owner = data.get("owner") or {}
        return {
            "full_name": data.get("full_name"),
            "owner": owner.get("login"),
            "visibility": data.get("visibility"),
            "default_branch": data.get("default_branch"),
            "archived": data.get("archived"),
            "html_url": data.get("html_url"),
        }
    if name == "get_commit_metadata":
        data = github_get(f"/repos/{quoted_repo}/commits/{urllib.parse.quote(COMMIT_SHA, safe='')}")
        commit = data.get("commit") or {}
        author = commit.get("author") or {}
        return {
            "sha": data.get("sha"),
            "message": commit.get("message"),
            "author_date": author.get("date"),
            "html_url": data.get("html_url"),
            "files": [
                {
                    key: item.get(key)
                    for key in ("filename", "status", "additions", "deletions", "changes")
                }
                for item in (data.get("files") or [])[:100]
            ],
        }
    if name == "get_check_runs":
        data = github_get(f"/repos/{quoted_repo}/commits/{urllib.parse.quote(COMMIT_SHA, safe='')}/check-runs?per_page=100")
        return {
            "total_count": data.get("total_count"),
            "check_runs": [
                {
                    key: item.get(key)
                    for key in ("name", "status", "conclusion", "started_at", "completed_at", "html_url")
                }
                for item in (data.get("check_runs") or [])[:100]
            ],
        }
    if name == "get_pull_request" and PULL_NUMBER:
        data = github_get(f"/repos/{quoted_repo}/pulls/{int(PULL_NUMBER)}")
        user = data.get("user") or {}
        return {
            "number": data.get("number"),
            "title": data.get("title"),
            "state": data.get("state"),
            "draft": data.get("draft"),
            "author": user.get("login"),
            "base_sha": (data.get("base") or {}).get("sha"),
            "head_sha": (data.get("head") or {}).get("sha"),
            "changed_files": data.get("changed_files"),
            "html_url": data.get("html_url"),
        }
    if name == "get_pull_request_files" and PULL_NUMBER:
        data = github_get(f"/repos/{quoted_repo}/pulls/{int(PULL_NUMBER)}/files?per_page=100")
        return [
            {
                key: item.get(key)
                for key in ("filename", "status", "additions", "deletions", "changes", "sha")
            }
            for item in data[:100]
        ]
    raise ValueError(f"Unknown or unavailable tool: {name}")


def result_text(value: Any) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=True)}]}


class Handler(BaseHTTPRequestHandler):
    server_version = "HermesBoundedMCP/1"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"mcp: {fmt % args}", flush=True)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json(200, {"status": "ok"})
        else:
            self._send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/mcp":
            self._send_json(404, {"error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY_BYTES:
                raise ValueError("invalid request size")
            request = json.loads(self.rfile.read(length))
            method = request.get("method")
            request_id = request.get("id")
            params = request.get("params") or {}

            if method == "notifications/initialized":
                self.send_response(202)
                self.end_headers()
                return
            if method == "initialize":
                response = {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "hermes-actions-bounded-github", "version": "1.0.0"},
                }
            elif method == "ping":
                response = {}
            elif method == "tools/list":
                response = {"tools": TOOLS}
            elif method == "tools/call":
                response = result_text(call_tool(params.get("name", ""), params.get("arguments")))
            else:
                self._rpc_error(request_id, -32601, "Method not found")
                return
            self._send_json(200, {"jsonrpc": "2.0", "id": request_id, "result": response})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._rpc_error(None, -32602, str(exc))
        except urllib.error.HTTPError as exc:
            self._rpc_error(None, -32001, f"GitHub API returned HTTP {exc.code}")
        except Exception as exc:
            self._rpc_error(None, -32603, f"Internal error: {type(exc).__name__}")

    def _rpc_error(self, request_id: Any, code: int, message: str) -> None:
        self._send_json(
            200,
            {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message[:300]}},
        )

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()