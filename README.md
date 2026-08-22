# Hermes Agent Evaluation Lab

This repository evaluates [Nous Research Hermes Agent](https://github.com/NousResearch/hermes-agent) for secure enterprise use and possible integration with an internal developer platform (IDP).

Research baseline: Hermes Agent `v0.20.5` / `v2026.8.19`, reviewed on 2026-08-22. Hermes changes quickly, so findings are versioned and should be revalidated before an architecture decision.

## Questions

1. What can Hermes do through its CLI, gateway, API, ACP, MCP, tools, skills, plugins, hooks, memory, and scheduled jobs?
2. Which controls are security boundaries, which are guardrails, and what remains the operator's responsibility?
3. Where can the long-running agent process and its tool execution run: host, container, Kubernetes, VM/HPC, or serverless sandbox?
4. Can Hermes safely augment an IDP without becoming a second authorization plane or a shared privileged bot?

## Working Conclusions

- The only boundary Hermes claims against an adversarial model is OS-level isolation. Approvals, deny patterns, redaction, tool filters, and content scanners are useful heuristics, not containment.
- A terminal backend isolates shell and file-tool execution, not necessarily the Hermes process, plugins, hooks, skills, or MCP subprocesses. Whole-process Docker or NVIDIA OpenShell is the stronger posture for untrusted input.
- Hermes directly supports seven terminal backends: local, Docker, SSH, Singularity/Apptainer, Modal, Daytona, and Vercel Sandbox.
- Kubernetes can host the long-running containerized agent, but it is not a native Hermes terminal backend. Stateful storage and single-writer behavior need explicit design.
- AWS Lambda and similar function runtimes are a poor fit for the stateful gateway process. Serverless sandboxes are viable as remote tool-execution backends; they do not automatically make the whole agent serverless.
- GitHub Actions is a good fit for bounded, one-shot Hermes tasks. Strong egress control requires a manually constructed Docker topology or network-controlled runner; a normal job container plus proxy environment variables is not containment.
- The strongest initial IDP fit is a single-tenant, least-privilege specialist behind existing platform APIs or narrowly filtered MCP tools. Hermes explicitly does not provide per-caller tool capabilities inside one adapter.

## Evaluation Method

Each finding is classified as one of:

- **Documented**: stated in official Hermes or dependency documentation.
- **Observed**: reproduced locally with commands and retained evidence.
- **Inferred**: architecture judgment derived from documented behavior.
- **Unknown**: requires an experiment or upstream clarification.

The project will contain:

- architecture and capability notes;
- a threat model and security-control inventory;
- a runtime decision matrix covering containers, Kubernetes, Lambda, and supported serverless backends;
- an IDP integration assessment and reference architecture;
- cautious configuration examples and repeatable evaluation scenarios;
- a source register pinned to the research baseline.

## Repository Map

- [Capabilities and architecture](docs/capabilities-and-architecture.md)
- [Security controls and limitations](docs/security-controls.md)
- [Runtime options](docs/runtime-options.md)
- [GitHub Actions runtime](docs/github-actions-runtime.md)
- [IDP feasibility](docs/idp-feasibility.md)
- [Evaluation plan](docs/evaluation-plan.md)
- [Research sources](research/sources.md)
- [Cautious evaluation config](config/cautious-evaluation.yaml)
- [Managed organization baseline](config/managed-baseline.yaml)
- [Docker evaluation deployment](deploy/docker/README.md)
- [GitHub Actions reference deployment](deploy/github-actions/README.md)

Run `make check` to validate local documentation links and basic repository invariants. The check has no third-party dependencies.

## Safety

Do not run destructive or exfiltration tests on a workstation, shared cluster, production account, or real repository. Use disposable infrastructure, synthetic credentials, an isolated network, and a dedicated test organization. Never mount a host Docker socket into an agent container during security evaluation.

## Upstream

- [Hermes Agent documentation](https://hermes-agent.nousresearch.com/docs/)
- [Hermes Agent security policy](https://github.com/NousResearch/hermes-agent/blob/main/SECURITY.md)
- [Hermes Agent source](https://github.com/NousResearch/hermes-agent)
- [NVIDIA OpenShell](https://github.com/NVIDIA/OpenShell)

Hermes Agent is MIT-licensed. This evaluation repository is independent of Nous Research and NVIDIA.

