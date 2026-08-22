#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
export GITHUB_WORKSPACE="${GITHUB_WORKSPACE:-${REPO_ROOT}}"
export RUNTIME_DIR="${RUNTIME_DIR:-${RUNNER_TEMP:-${TMPDIR:-/tmp}}/hermes-actions-${GITHUB_RUN_ID:-local}}"
export COMPOSE_PROJECT_NAME="hermes-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}"
export GITHUB_REPOSITORY="${GITHUB_REPOSITORY:-local/hermes-evaluation}"
export GITHUB_SHA="${GITHUB_SHA:-local}"
export GITHUB_RUN_ID="${GITHUB_RUN_ID:-local}"

: "${HERMES_PROMPT:?Set HERMES_PROMPT}"
: "${HERMES_MODEL:?Set HERMES_MODEL}"
: "${HERMES_PROVIDER:=custom}"
: "${COPILOT_GITHUB_TOKEN:?Set COPILOT_GITHUB_TOKEN}"
: "${MCP_AUTH_TOKEN:?Set MCP_AUTH_TOKEN}"
: "${HERMES_IMAGE:?Set HERMES_IMAGE to a pinned digest}"
: "${MITMPROXY_IMAGE:?Set MITMPROXY_IMAGE to a pinned digest}"

case "${COPILOT_GITHUB_TOKEN}" in
    gho_*|github_pat_*|ghu_*) ;;
    *)
        echo "ERROR: COPILOT_GITHUB_TOKEN must be gho_*, github_pat_*, or ghu_*; the normal Actions github.token is not a Copilot credential" >&2
        exit 1
        ;;
esac

compose=(docker compose -f "${SCRIPT_DIR}/compose.yaml")

on_error() {
    status="$1"
    set +e
    echo "ERROR: Hermes Actions stack failed; container status and recent logs follow" >&2
    "${compose[@]}" ps --all >&2
    "${compose[@]}" logs --no-color --tail 200 >&2
    exit "${status}"
}

cleanup() {
    "${compose[@]}" down --volumes --remove-orphans >/dev/null 2>&1 || true
    rm -rf "${RUNTIME_DIR}/secrets"
}
trap 'on_error $?' ERR
trap cleanup EXIT INT TERM

install -d -m 0700 "${RUNTIME_DIR}/secrets" "${RUNTIME_DIR}/hermes"
install -m 0600 /dev/null "${RUNTIME_DIR}/secrets/copilot_token"
install -m 0600 /dev/null "${RUNTIME_DIR}/secrets/mcp_auth_token"
printf '%s' "${COPILOT_GITHUB_TOKEN}" >"${RUNTIME_DIR}/secrets/copilot_token"
printf '%s' "${MCP_AUTH_TOKEN}" >"${RUNTIME_DIR}/secrets/mcp_auth_token"
install -m 0600 "${SCRIPT_DIR}/config.yaml" "${RUNTIME_DIR}/hermes/config.yaml"
unset COPILOT_GITHUB_TOKEN MCP_AUTH_TOKEN

"${compose[@]}" build mcp
"${compose[@]}" up -d --wait --wait-timeout 60 proxy
"${compose[@]}" exec -T proxy cat /mitmproxy-conf/mitmproxy-ca-cert.pem \
    >"${RUNTIME_DIR}/mitmproxy-ca-cert.pem"
chmod 0444 "${RUNTIME_DIR}/mitmproxy-ca-cert.pem"
"${compose[@]}" up -d --wait --wait-timeout 60 mcp

# An internal Docker network must have no direct external route. This test uses
# an IP address so a DNS failure cannot create a false pass.
if "${compose[@]}" run --rm --no-deps --entrypoint /opt/hermes/.venv/bin/python hermes -c \
    'import socket; socket.create_connection(("1.1.1.1", 443), 3)' 2>/dev/null; then
    echo "ERROR: Hermes has direct external network access" >&2
    exit 1
fi

"${compose[@]}" run --rm --no-deps --entrypoint /opt/hermes/.venv/bin/python hermes -c \
    'import urllib.request; urllib.request.urlopen("http://mcp:8080/health", timeout=5).read()'

"${compose[@]}" run --rm --no-deps hermes \
    chat --provider "${HERMES_PROVIDER}" --model "${HERMES_MODEL}" --run-budget 3000 -q "${HERMES_PROMPT}" \
    | tee "${RUNTIME_DIR}/result.md"

printf 'Hermes result retained at %s\n' "${RUNTIME_DIR}/result.md"