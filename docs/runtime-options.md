# Runtime Options

Status: documented for native Hermes options; inferred for Kubernetes and function platforms. Baseline: Hermes Agent v0.20.5.

## Two Independent Decisions

1. **Agent runtime:** where the stateful Hermes process, gateway, API, extensions, and session database run.
2. **Tool runtime:** where model-requested shell, file, and code operations run.

Calling both of these “the runtime” hides the most important security trade-off.

## Agent Runtime Matrix

| Option | Support | Fit | Notes |
| --- | --- | --- | --- |
| Workstation/native VM | Documented | Evaluation only | Default local tools share the user's access; systemd/launchd supports a long-running gateway |
| Official Docker image | First-class | Good pilot baseline | Whole-process container, non-root runtime, immutable install tree, persistent `/opt/data` |
| GitHub-hosted Actions runner | Inferred/container-compatible | Good for one-shot work | Ephemeral VM, six-hour job limit, native workflow identity; requires an inner network topology for enforceable egress |
| Kubernetes | Inferred/container-compatible | Feasible with care | No official Hermes Kubernetes deployment; run one writer per state volume and test entrypoint behavior |
| OpenShell on Kubernetes | Experimental upstream path | Promising for stronger policy | Adds filesystem, egress, process, inference, and provider controls; Helm path is explicitly experimental |
| Long-lived VM on IaaS | Documented deployment style | Good | Straightforward state and service lifecycle; coarser scaling and isolation |
| AWS Lambda/function runtime | Not first-class | Poor | Gateway, SQLite state, background processes, long model calls, SSE, and approvals conflict with function lifecycle |
| Container serverless service | Inferred | Conditional | Can host the agent if it supports long requests, persistent state, private networking, and single-writer semantics |

## Tool Runtime Matrix

| Backend | Isolation target | Persistence | Best use |
| --- | --- | --- | --- |
| `local` | None | Host filesystem | Trusted local development |
| `docker` | Local container | Shared persistent or per-session ephemeral | Reproducible local/CI sandbox |
| `ssh` | Remote account/host | Remote filesystem | Dedicated worker VM or powerful hardware |
| `singularity` | HPC container | Writable overlay | Shared HPC environments |
| `modal` | Cloud VM sandbox | Filesystem snapshot | Elastic evaluations and burst compute |
| `daytona` | Managed workspace | Stop/resume | Persistent cloud development workspace |
| `vercel_sandbox` | Cloud microVM | Filesystem snapshot | Node/Python cloud command execution |

Modal, Daytona, and Vercel are serverless **tool backends**. The controlling Hermes process still runs somewhere else. Snapshot persistence preserves files, not process identity, PID state, or detached jobs.

## GitHub Actions Feasibility

GitHub-hosted runners are a strong evaluation and batch-execution option:

- each standard hosted job receives a fresh VM;
- the workflow provides an existing trigger, identity, logs, timeout, concurrency, and artifact lifecycle;
- one-shot `hermes chat -q` work does not need gateway persistence;
- custom containers can isolate Hermes from credentials held by sidecars.

The default Actions container model is insufficient for hard egress control. Job and service containers share a user-defined bridge and can reach the internet. GitHub does not support `--network` in `jobs.<job>.container.options`. Setting `HTTP_PROXY` only asks cooperative software to use a proxy; agent-run code can unset it or open a direct socket.

For GitHub-hosted runners, run orchestration steps on the runner and create an inner Docker network marked `internal`. Attach Hermes only to that network. Attach an allowlisting proxy to both the internal and external networks, and keep model-provider and platform credentials in separate LLM-gateway and MCP containers. See [GitHub Actions runtime](github-actions-runtime.md).

## Kubernetes Feasibility

Kubernetes is viable for the official container image, with these design constraints:

- Start with one pod and one persistent volume. Hermes warns against concurrent gateways sharing the same data directory.
- Use a StatefulSet or a Deployment fixed at one replica; do not assume horizontal scaling over one `HERMES_HOME`.
- Place the API behind ClusterIP plus an identity-aware gateway. Keep `API_SERVER_KEY` as defense in depth.
- Use `/health` for liveness and authenticated `/health/detailed` content for readiness logic.
- Mount secrets from the platform secret store and non-secret managed policy read-only. Do not put secrets in the world-readable managed `.env` model.
- Apply a restricted security context, default-deny NetworkPolicy, seccomp, resource limits, and a dedicated service account with no Kubernetes API access unless explicitly needed.
- Never mount the host Docker socket. Use a remote sandbox backend or separate worker service.
- Test the image entrypoint. Hermes documents a fallback without s6 supervision when another init owns PID 1, including some Kubernetes setups.
- Treat upgrades as stateful migrations: back up the volume, pin image digests, and exercise rollback.

Kubernetes does not solve per-user authorization or safe tool design. It provides scheduling and isolation primitives on which those controls can be built.

## Lambda and Serverless Feasibility

Direct Lambda hosting is not recommended because Hermes expects a long-lived process with local state, asynchronous platform connections, background work, approvals, and potentially long tool/model runs. A function wrapper would have to externalize nearly every lifecycle assumption and would no longer resemble the supported gateway.

Better decompositions:

- Run Hermes on a small long-lived container/VM and invoke serverless sandboxes for tools.
- Use the Runs API from the IDP and let Kubernetes or a container service own Hermes lifecycle.
- Use event-driven functions around Hermes for admission, credential vending, audit ingestion, and notifications.

## Recommended Progression

1. GitHub Actions one-shot analysis with an internal Docker network and credential-bearing sidecars.
2. Official Docker image on a dedicated evaluation host for interactive or longer-lived work.
3. Single-replica Kubernetes pilot with private API access and external policy/identity.
4. OpenShell evaluation if L7 egress, inference routing, or credential isolation is a hard requirement.
5. Modal/Daytona/Vercel comparison only for tool workloads that benefit from their persistence and cost model.

## Sources

See [the source register](../research/sources.md), especially S01, S02, S04, S05, S11, S13, S14, and S15.