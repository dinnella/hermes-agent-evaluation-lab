# Security Controls and Limitations

Status: documented unless marked as an evaluation requirement. Baseline: Hermes Agent v0.20.5.

## Security Thesis

Hermes' security policy states that the operating system is the only security boundary against an adversarial LLM. Everything that screens attacker-influenced strings inside the agent process is a heuristic. This distinction should control the deployment design.

## Boundary Matrix

| Control | Class | Protects | Does not protect |
| --- | --- | --- | --- |
| Whole-process Docker | OS boundary | Agent, tools, MCP children, plugins, hooks, skills within container policy | Overbroad mounts, socket exposure, permissive egress, kernel/runtime flaws |
| NVIDIA OpenShell | OS/policy boundary | Filesystem, process/syscall, network egress, inference routing, credential injection | Misconfigured policy and experimental deployment paths |
| Docker/Modal/Daytona/Vercel terminal backend | OS boundary for tool runtime | Shell and file tools; test `execute_code` routing for the pinned version | Agent process, in-process extensions, host-side MCP/plugins/hooks |
| SSH terminal backend | Host/network separation | Keeps shell/file work off the agent host | Security of the remote account and host |
| Approvals and deny patterns | Guardrail | Common destructive-command mistakes | Adversarial shell construction; isolated backends may skip guards |
| File safe root and protected paths | Guardrail | `write_file` and `patch` targets | Writes performed through terminal or in-process code |
| Secret redaction | Guardrail | Common key/token patterns in model context and logs | Encoded, fragmented, or novel exfiltration |
| Tool/MCP filters | Capability reduction | Hides unneeded registered tools | In-process malicious code or an allowed general-purpose terminal |
| Environment filtering | Exposure reduction | Accidental secret inheritance by subprocesses | In-process components and explicitly forwarded credentials |
| SSRF checks and website blocklist | Network guardrail | URL-capable built-in tools | Arbitrary sockets/subprocess networking without OS egress policy |
| Managed scope | Admin configuration control | User override of pinned keys on a correctly permissioned host | Root, writable policy dirs, repointed `HERMES_MANAGED_DIR`, agent escape |

## Built-In Controls

- Gateway allowlists and DM pairing default to deny unknown users.
- Dangerous-command prompts fail closed after the configured timeout.
- A hardline blocklist and user deny rules remain active under YOLO mode.
- Secret redaction and context-file injection scanning are enabled by default.
- MCP stdio processes receive a small safe environment plus explicitly configured variables.
- URL-capable tools reject private, loopback, link-local, CGNAT, and cloud metadata targets by default and revalidate redirects.
- Docker terminal containers drop capabilities, disable privilege escalation, limit PIDs, and use bounded temporary filesystems.
- Checkpoints can snapshot project changes before destructive operations, but are opt-in.
- Skill writes and memory writes can be approval-gated, but both are opt-in.
- Tirith command scanning is enabled by default but fails open by default and may be unavailable on some platforms.
- Runtime lazy dependency installation is enabled by default and can be disabled.
- Tool-loop warnings are enabled, while hard stops are disabled by default.

## High-Risk Gaps

1. **Untrusted input plus local execution:** Prompt injection is expected, not considered a vulnerability by itself. Containment must assume eventual model compromise.
2. **Plugins and skills:** Python can execute at import time with agent privileges. Manifest capabilities are consent/audit controls, not a sandbox.
3. **MCP:** An stdio MCP server is executable code; an HTTP MCP server can return hostile content. Sampling is enabled by default and can create additional model use.
4. **API authorization:** A valid API key grants access to the agent's full effective toolset. Put enterprise authentication and authorization in front of it.
5. **Shared callers:** Hermes does not enforce per-caller tools inside one adapter. Separate instances/profiles and upstream policy are required.
6. **Credential forwarding:** Any secret deliberately passed to a sandbox must be considered readable and exfiltratable by that workload.
7. **Docker socket:** Mounting `/var/run/docker.sock` gives practical host control and defeats container containment.
8. **Persistent sandboxes:** Reused filesystems can carry data and credentials across sessions. Per-session ephemeral mode should be evaluated for shared use.
9. **Documentation drift:** The security policy and runtime documentation are not perfectly aligned on `execute_code` containment. Whole-process isolation avoids depending on that ambiguity.

## Required Enterprise Posture

- Run the whole Hermes process as a non-root user in an OS sandbox.
- Default-deny egress at the runtime layer; allow only model, source-control, artifact, and approved IDP endpoints.
- Keep the API on a private network behind the IDP's identity-aware gateway.
- Use one security principal and one isolated workspace per task or user boundary.
- Expose narrow, task-specific HTTP MCP tools instead of cloud CLIs with broad credentials.
- Use short-lived workload identity issued by the IDP; do not forward human credentials.
- Disable runtime package installation and unreviewed plugins/skills in managed environments.
- Enable checkpoints, skill/memory write approval, tool-loop hard stops, run budgets, and fail-closed policy hooks.
- Export redacted audit events to a durable external system; Hermes outbound webhooks are best-effort, not guaranteed delivery.

## Evaluation Gates

See [the evaluation plan](evaluation-plan.md). No production pilot should begin until filesystem, egress, credential, caller-isolation, approval, and audit tests pass in the target runtime.

## Sources

See [the source register](../research/sources.md), especially S02, S03, S05, S09, and S10.