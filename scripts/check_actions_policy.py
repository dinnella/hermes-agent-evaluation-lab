#!/usr/bin/env python3
"""Check security-critical invariants in the Actions reference deployment."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTIONS_DIR = ROOT / "deploy" / "github-actions"


def require(text: str, value: str, source: str, failures: list[str]) -> None:
    if value not in text:
        failures.append(f"{source}: required text is missing: {value!r}")


def reject(text: str, value: str, source: str, failures: list[str]) -> None:
    if value in text:
        failures.append(f"{source}: forbidden text is present: {value!r}")


def main() -> int:
    failures: list[str] = []
    compose = (ACTIONS_DIR / "compose.yaml").read_text(encoding="utf-8")
    config = (ACTIONS_DIR / "config.yaml").read_text(encoding="utf-8")
    proxy = (ACTIONS_DIR / "mitmproxy" / "policy.py").read_text(encoding="utf-8")
    workflow = (ACTIONS_DIR / "workflow-template.yaml").read_text(encoding="utf-8")
    active_workflow = (ROOT / ".github" / "workflows" / "hermes-analysis.yaml").read_text(
        encoding="utf-8"
    )

    hermes_block = compose.split("  hermes:\n", 1)[1].split("\nnetworks:\n", 1)[0]
    require(compose, "  agent:\n    internal: true", "compose.yaml", failures)
    require(compose, '    user: "1000:1000"', "compose.yaml", failures)
    require(compose, "      - /usr/local/bin/mitmdump", "compose.yaml", failures)
    require(compose, "      - /mitmproxy-conf:uid=1000,gid=1000,mode=0700", "compose.yaml", failures)
    require(hermes_block, "${GITHUB_WORKSPACE:?Set GITHUB_WORKSPACE}:/workspace:ro", "compose.yaml", failures)
    reject(hermes_block, "external:", "compose.yaml hermes service", failures)
    reject(hermes_block, "copilot_token", "compose.yaml hermes service", failures)
    reject(compose, "docker.sock", "compose.yaml", failures)
    reject(compose, "mitmproxy-conf: {}", "compose.yaml", failures)

    launcher = (ACTIONS_DIR / "run.sh").read_text(encoding="utf-8")
    require(
        launcher,
        'exec -T proxy cat /mitmproxy-conf/mitmproxy-ca-cert.pem',
        "run.sh",
        failures,
    )
    reject(launcher, "cp proxy:/mitmproxy-conf", "run.sh", failures)

    require(proxy, 'host != "api.githubcopilot.com"', "mitmproxy/policy.py", failures)
    require(proxy, 'host != "api.github.com"', "mitmproxy/policy.py", failures)
    require(proxy, 'f"Bearer {SENTINEL}"', "mitmproxy/policy.py", failures)
    require(proxy, 'flow.request.headers["Authorization"] = f"Bearer {COPILOT_TOKEN}"', "mitmproxy/policy.py", failures)
    require(proxy, 'deny(flow, 403, "source_not_allowed")', "mitmproxy/policy.py", failures)

    require(config, "single_query_mode: deny", "config.yaml", failures)
    require(config, "hard_stop_enabled: true", "config.yaml", failures)
    reject(config.lower(), "yolo", "config.yaml", failures)

    require(workflow, "permissions:", "workflow-template.yaml", failures)
    require(workflow, "  contents: read", "workflow-template.yaml", failures)
    reject(workflow, "contents: write", "workflow-template.yaml", failures)
    require(workflow, "COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}", "workflow-template.yaml", failures)
    require(workflow, "HERMES_IMAGE: nousresearch/hermes-agent@sha256:", "workflow-template.yaml", failures)
    require(workflow, "MITMPROXY_IMAGE: mitmproxy/mitmproxy@sha256:", "workflow-template.yaml", failures)
    require(workflow, "MCP_AUTH_TOKEN: ${{ github.token }}", "workflow-template.yaml", failures)
    reject(workflow, "pull_request_target", "workflow-template.yaml", failures)
    if active_workflow != workflow:
        failures.append("active Hermes workflow differs from deploy/github-actions/workflow-template.yaml")

    if failures:
        print("GitHub Actions policy validation failed:")
        print("\n".join(f"- {failure}" for failure in failures))
        return 1

    print("Validated GitHub Actions isolation policy invariants.")
    return 0


if __name__ == "__main__":
    sys.exit(main())