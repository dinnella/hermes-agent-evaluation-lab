#!/usr/bin/env python3
"""Exercise mitmproxy policy decisions with a minimal in-process stub."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "deploy" / "github-actions" / "mitmproxy" / "policy.py"


class Headers(dict):
    def get(self, key: str, default=None):
        for current, value in self.items():
            if current.lower() == key.lower():
                return value
        return default

    def setdefault(self, key: str, default=None):
        existing = self.get(key)
        if existing is not None:
            return existing
        self[key] = default
        return default


class Response:
    @staticmethod
    def make(status: int, content: str, headers: dict) -> types.SimpleNamespace:
        return types.SimpleNamespace(status_code=status, text=content, headers=headers, stream=False)


def flow(source: str, host: str, path: str, token: str, model: str = "gpt-5.4"):
    request = types.SimpleNamespace(
        pretty_host=host,
        path=path,
        headers=Headers({"Authorization": f"Bearer {token}"}),
        raw_content=json.dumps({"model": model}).encode("utf-8"),
    )
    return types.SimpleNamespace(
        client_conn=types.SimpleNamespace(peername=(source, 12345)),
        request=request,
        response=None,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        token_path = Path(temp_dir) / "copilot-token"
        token_path.write_text("real-copilot-credential", encoding="utf-8")
        os.environ.update(
            {
                "GATEWAY_HERMES_IP": "172.30.0.10",
                "GATEWAY_MCP_IP": "172.30.0.20",
                "GATEWAY_SENTINEL": "sentinel",
                "GATEWAY_ALLOWED_MODELS": "gpt-5.4",
                "COPILOT_TOKEN_FILE": str(token_path),
            }
        )
        http_module = types.ModuleType("mitmproxy.http")
        http_module.HTTPFlow = object
        http_module.Response = Response
        mitmproxy_module = types.ModuleType("mitmproxy")
        mitmproxy_module.http = http_module
        sys.modules["mitmproxy"] = mitmproxy_module
        sys.modules["mitmproxy.http"] = http_module

        spec = importlib.util.spec_from_file_location("actions_mitm_policy", POLICY_PATH)
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not load mitmproxy policy module")
        policy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(policy)

        allowed = flow("172.30.0.10", "api.githubcopilot.com", "/responses", "sentinel")
        policy.request(allowed)
        assert allowed.response is None
        assert allowed.request.headers["Authorization"] == "Bearer real-copilot-credential"

        wrong_sentinel = flow("172.30.0.10", "api.githubcopilot.com", "/responses", "wrong")
        policy.request(wrong_sentinel)
        assert wrong_sentinel.response.status_code == 401

        wrong_host = flow("172.30.0.10", "example.com", "/responses", "sentinel")
        policy.request(wrong_host)
        assert wrong_host.response.status_code == 403

        wrong_model = flow("172.30.0.10", "api.githubcopilot.com", "/responses", "sentinel", "other")
        policy.request(wrong_model)
        assert wrong_model.response.status_code == 403

        unknown_source = flow("172.30.0.99", "api.githubcopilot.com", "/responses", "sentinel")
        policy.request(unknown_source)
        assert unknown_source.response.status_code == 403

    print("Validated mitmproxy source, host, model, sentinel, and credential injection policy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())