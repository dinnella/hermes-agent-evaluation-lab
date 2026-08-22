# GitHub Actions Reference Deployment

This reference runs one Hermes task inside a disposable container on a GitHub-hosted runner. The active workflow is installed at [../../.github/workflows/hermes-analysis.yaml](../../.github/workflows/hermes-analysis.yaml); it cannot run until the repository has a GitHub remote, the workflow is pushed, and the required secret and variables are configured.

## Security Properties

- Hermes joins only an internal Docker network with no direct internet route.
- A source-aware mitmproxy instance is the only container attached to an external network.
- Mitmproxy owns the Copilot credential and replaces only an exact non-secret sentinel from Hermes.
- The HTTP MCP service owns the GitHub or IDP credential.
- Hermes receives the sentinel and an ephemeral mitmproxy CA certificate, never the Copilot or GitHub credential.
- The repository is mounted read-only for the analysis profile.
- The Docker socket is never mounted into Hermes.
- The launcher tests direct egress and aborts if it unexpectedly succeeds.

See [the full architecture assessment](../../docs/github-actions-runtime.md) before using the template.

## Implemented Sidecars

The reference includes both policy components needed for a first test.

### Mitmproxy credential and egress gateway

- runs in regular forward-proxy mode and is the only dual-homed container;
- generates a per-job CA; the launcher mounts only its public certificate into Hermes and MCP;
- permits Hermes only to `api.githubcopilot.com` on the allowed API paths and models;
- requires `Authorization: Bearer hermes-copilot-sentinel`, then substitutes the real token from its Docker secret;
- permits MCP only to repository paths on `api.github.com`;
- denies every other source or destination and streams model responses without writing flow archives.

### Bounded GitHub MCP

- listens on `0.0.0.0:8080` with Streamable HTTP MCP at `/mcp`;
- reads its token from `/run/secrets/mcp_auth_token`;
- accepts `HTTP_PROXY` and `HTTPS_PROXY` for upstream calls;
- exposes read-only workflow context, repository, commit, checks, and optional pull-request tools;
- takes no model-supplied repository, SHA, or pull-request target arguments;
- contains no general shell or arbitrary URL-fetch tool.

Mitmproxy is intentionally used as an inspecting forward proxy, so its CA must be trusted by the two clients. This is not transparent mode and requires no host routing privileges. The CA private key remains in the proxy-only tmpfs; only the public CA certificate is copied out.

The CA state is held on a UID-owned tmpfs. Docker cannot archive files from that mount with `docker cp`, so the launcher streams the public certificate through `docker compose exec`; the private key is never copied to the runner filesystem.

The sample deliberately keeps `security.allow_private_urls: false`. In the pinned Hermes baseline, native configured HTTP MCP servers use the MCP client path rather than the web/browser URL-tool SSRF gate, and native URL validation accepts HTTP(S) endpoints. Verify this against the selected Hermes image before use. Do not enable private URLs globally merely to make the sidecar reachable.

## Files

- [compose.yaml](compose.yaml): isolated container topology
- [config.yaml](config.yaml): unattended Hermes policy
- [mitmproxy/policy.py](mitmproxy/policy.py): source, destination, path, model, and sentinel policy
- [run.sh](run.sh): secret staging, startup, egress assertion, agent run, cleanup
- [workflow-template.yaml](workflow-template.yaml): source template for the active read-only workflow

## Installation

1. Review the checked-in image digests. The workflow pins Hermes `v2026.8.19` for Linux/amd64 and mitmproxy `12.2.3`; the MCP image is built from this repository.
2. Review the mitmproxy policy and MCP tool includes.
3. Review the installed `.github/workflows/hermes-analysis.yaml` against the template.
4. Pin the checkout action to a reviewed full commit SHA.
5. Configure `COPILOT_GITHUB_TOKEN` as a repository or protected-environment secret.
6. Protect workflow and deployment files with CODEOWNERS.
7. Run only from a protected branch until the untrusted-PR/no-secrets profile has separate infrastructure.

The normal `${{ github.token }}` cannot power Copilot inference. Use a Copilot-capable OAuth token (`gho_*`) or GitHub App user-to-server token (`ghu_*`) as `COPILOT_GITHUB_TOKEN`. The workflow's ordinary token remains confined to MCP for read-only repository API calls.

GitHub documents user-owned fine-grained PATs with `Copilot Requests` for **Copilot CLI**, but the direct `api.githubcopilot.com` endpoint used by this Hermes integration rejected the tested PAT with `HTTP 400: Personal Access Tokens are not supported for this endpoint`. The launcher now rejects `github_pat_*` credentials before starting containers. This is an observed direct-API limitation, not a claim that the same PAT cannot work through GitHub's own Copilot CLI.

For the current smoke test, `gh auth token` produced a `gho_*` token and a direct request to the Copilot model catalog returned HTTP 200. That OAuth token has broader GitHub CLI scopes than a dedicated inference credential, so store it only in the protected repository secret, keep the workflow manual/read-only, and rotate it after the evaluation. A dedicated `copilot login` OAuth token is preferable when its credential can be exported into the secret store without exposing it.

Pinned image references:

- `nousresearch/hermes-agent@sha256:f3cba6abf5ed80d47a271498d663ace5dda87f45000552afb8be8370a35df1b5`
- `mitmproxy/mitmproxy@sha256:68afa70d7b6ac9d269b88f88534f9ffceb363b4ce31703a78702341fba82e831`

These are platform-specific Linux/amd64 image manifests, matching `ubuntu-24.04` hosted runners. Re-resolve and review digests when changing the runner architecture or dependency versions.

The sentinel replacement works because mitmproxy terminates the proxied TLS connection using its per-job CA. A non-inspecting Squid `CONNECT` tunnel could restrict destinations but could not see or replace the encrypted `Authorization` header. Mitmproxy validates the exact source, host, path, model, and sentinel before substituting the real credential.

## First Smoke Prompt

Use a prompt that proves both local file access and bounded MCP operation:

```text
Use get_workflow_context and get_repository_metadata from the platform MCP. Then read README.md from the mounted checkout. In five bullets, distinguish facts obtained from MCP from facts read from the repository. Do not modify files.
```

The run is successful only when direct socket egress fails, the Copilot request succeeds through mitmproxy, both MCP tools execute, the checkout remains unchanged, and no credential appears in logs.

## Troubleshooting

### Proxy exits with code 3 during startup

The upstream mitmproxy image entrypoint uses `stat` and `usermod` before dropping privileges. It fails when all capabilities are already dropped, producing errors such as `stat: Permission denied` and `usermod: invalid user ID '-g'`.

The reference bypasses that entrypoint, runs `/usr/local/bin/mitmdump` directly as UID/GID 1000, and supplies a UID-owned tmpfs for CA state. Do not remove those Compose settings without rerunning the hardened-container startup test.

Docker cannot archive files from that tmpfs with `docker cp`. The launcher therefore reads the public CA using `docker compose exec -T proxy cat ...`. On any launcher failure it prints Compose status and the last 200 log lines before cleanup.

### Sidecar cannot read `/run/secrets/...`

Local Docker Compose implements file-backed secrets as read-only bind mounts and preserves the source file mode. A runner-owned `0600` file is unreadable to mitmproxy UID 1000 and the MCP UID 65532. The launcher stages each secret as read-only `0444` inside a runner-owned `0700` directory; the host directory prevents unrelated host users from traversing to the file, and Compose mounts each secret only into its intended sidecar.

### `HTTP 400: Personal Access Tokens are not supported`

The request reached Copilot, but the direct inference endpoint rejected a `github_pat_*` token even though GitHub documents that token type for Copilot CLI automation. Replace the Actions secret with a Copilot-capable OAuth `gho_*` token or supported `ghu_*` app-user token. Do not weaken the proxy or forward the job `${{ github.token }}` as a workaround.

For production, put orchestration in a centrally owned reusable workflow pinned by SHA. A checked-out repository must not be able to replace the launcher that stages credentials.

## Mutation Path

Do not add write permission to the analysis workflow. Create a separate workflow that:

- uses `workflow_dispatch` or a trusted reusable-workflow caller;
- targets a protected environment with required reviewers;
- grants only the required `contents` or `pull-requests` permission;
- uses a distinct mutation MCP image/tool allowlist;
- verifies repository, target SHA, policy decision, and proposed artifact digest;
- creates a branch and pull request instead of pushing to the default branch.

The mutation MCP service, not Hermes, should own the write token and final authorization decision.