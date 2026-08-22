# Docker Evaluation Deployment

This starts the whole Hermes agent in the official image and exposes its API on host loopback only. It is a research baseline, not a production deployment.

## Setup

1. Copy `.env.example` to `.env` and replace the API key placeholder with a random value.
2. Create the state directory: `mkdir -p deploy/docker/.state/hermes`.
3. Run the Hermes setup wizard against that directory before starting the gateway:

   ```bash
   docker run -it --rm \
     -v "$PWD/deploy/docker/.state/hermes:/opt/data" \
     nousresearch/hermes-agent:latest setup
   ```

4. Validate and start:

   ```bash
   docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml config
   docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml up -d
   ```

5. Query liveness at `http://127.0.0.1:8642/health`. Authenticated API calls use the bearer key in `.env`.

## Boundaries

- This container wraps the Hermes process, but its writable state is deliberately mounted at `.state/hermes`.
- The sample does not mount a source repository, cloud credentials, or the Docker socket.
- A Docker terminal backend would require access to a Docker daemon and would weaken this simple boundary if implemented through a host socket. Prefer a remote sandbox for that experiment.
- The sample leaves dashboard and messaging channels disabled.
- Delete `.state` after the evaluation if no evidence needs to be retained.