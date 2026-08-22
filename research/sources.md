# Source Register

Accessed 2026-08-22. Mutable documentation is evaluated against Hermes Agent v0.20.5 / release v2026.8.19. Pin source commits or archive rendered pages before a formal decision.

| ID | Source | Primary evidence |
| --- | --- | --- |
| S01 | [Hermes README](https://github.com/NousResearch/hermes-agent) | Product scope, entry points, seven terminal backends, installation, license |
| S02 | [Hermes security policy](https://github.com/NousResearch/hermes-agent/blob/main/SECURITY.md) | Trust model, OS boundary, terminal-versus-process isolation, plugin trust, scope |
| S03 | [Security guide](https://hermes-agent.nousresearch.com/docs/user-guide/security) | Approvals, file guards, gateway auth, environment filtering, SSRF, Tirith, hardening |
| S04 | [Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration) | Backend details, persistence, limits, toolsets, memory, hooks, security defaults |
| S05 | [Docker](https://hermes-agent.nousresearch.com/docs/user-guide/docker) | Whole-process image, state volume, non-root model, API exposure, lifecycle, Kubernetes PID 1 caveat |
| S06 | [Architecture](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture) | AIAgent, entry points, storage, tool registry, plugin and gateway architecture |
| S07 | [API server](https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server) | Auth, endpoints, runs/sessions/jobs APIs, health, concurrency, capabilities, limitations |
| S08 | [MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp) | Stdio/HTTP tools, filtering, OAuth/mTLS, identity headers, sampling, Hermes MCP server |
| S09 | [Managed scope](https://hermes-agent.nousresearch.com/docs/user-guide/managed-scope) | Admin precedence, filesystem enforcement, managed-secret and relocation limitations |
| S10 | [Hooks](https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks) | Policy/observer hooks, fail-open/closed behavior, sensitive payloads, signed webhooks |
| S11 | [NVIDIA OpenShell](https://github.com/NVIDIA/OpenShell) | Whole-process policy domains, providers, compute drivers, experimental Kubernetes Helm path |
| S12 | [ACP](https://hermes-agent.nousresearch.com/docs/user-guide/features/acp) | Editor integration, curated toolset, approval-host caveat, process-scoped sessions |
| S13 | [Running Actions jobs in a container](https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/run-jobs-in-a-container) | Job containers, mounts, resource options, unsupported network/entrypoint options |
| S14 | [Actions service containers](https://docs.github.com/en/actions/use-cases-and-examples/using-containerized-services/about-service-containers) | Bridge networking, service discovery, port mapping, lifecycle |
| S15 | [GitHub Actions secure use](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions) | Least privilege, untrusted checkout, script injection, action pinning, runner risks |
| S16 | [GitHub Actions OIDC](https://docs.github.com/en/actions/concepts/security/openid-connect) | Job identity claims, short-lived credential exchange, trust-policy boundary |
| S17 | [GitHub Actions limits](https://docs.github.com/en/actions/reference/limits) | Six-hour hosted job limit, concurrency, storage, queue and API limits |
| S18 | [Hermes AI providers](https://hermes-agent.nousresearch.com/docs/integrations/providers) | Copilot token types, direct API behavior, model routing, ACP alternative |
| S19 | [Copilot CLI installation](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli) | Subscription prerequisite and fine-grained PAT Copilot Requests permission |
| S20 | [Mitmproxy proxy modes](https://docs.mitmproxy.org/stable/concepts/modes/) | Regular, reverse, transparent, and upstream modes; reverse fixed-target behavior |
| S21 | [Mitmproxy certificates](https://docs.mitmproxy.org/stable/concepts/certificates/) | Per-install CA generation and downstream trust requirements |
| S22 | [Mitmproxy addon examples](https://docs.mitmproxy.org/stable/addons/examples/) | Request header mutation, synthetic denials, and response streaming hooks |

## Verification Notes

- The Hermes security policy is authoritative when product-guide wording appears stronger than the named boundary.
- “Supported” means documented first-class behavior, not merely that a Python process can run on a platform.
- Kubernetes and Lambda conclusions in this repository are architecture inferences, explicitly labeled as such.
- OpenShell is a separate NVIDIA project and adds its own maturity, telemetry, licensing, and operational considerations.