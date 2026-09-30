# Quick project reference

## Prerequisites

- [Docker](https://docs.docker.com/engine/install/)
- [docker-compose](https://docs.docker.com/compose/install/) >= 2
- (Optional) [Vim](https://www.vim.org/) or other text editor - for configuration and development

Please note it is important to use the abovementioned version of
`docker-compose` or newer, otherwise the build and deploy will fail.

## Deployment

Clone via git

```
git clone --depth 1  https://github.com/taranis-ai/taranis-ai
cd taranis-ai/docker/
```

## Configuration

Copy env.sample to .env

```
cp env.sample .env
```

Open file `.env` and defaults if needed

### Settings preseeding

Before the first startup, pass `PRE_SEED_SETTINGS` to the core container as a flat JSON object using the keys stored in Admin Settings. Any subset (or all settings) can be supplied; omitted keys retain their built-in defaults. The shipped Compose files (including load, minimal, PPN, and Tor variations) forward this variable from your shell or `.env`, defaulting to `{}`. For example, add this line to `.env`:

```dotenv
PRE_SEED_SETTINGS='{"default_timezone":"Europe/Vienna","rss_collector_max_entries":100,"default_bot_lookback_days":0,"onboarding_enabled":false}'
```

For a directly launched core process, export the same JSON value as `PRE_SEED_SETTINGS`. For Kubernetes, set `PRE_SEED_SETTINGS` in `deploy/kubernetes/00-config.yaml`; for Helm, set `config.preSeedSettings` to the same JSON string. These ConfigMap values must not contain credentials; inject credential-bearing seeds into the core environment through a Secret instead.

Preseeding applies only when the persistent settings row does not exist. Restarts and upgrades preserve saved settings, including administrator edits; they do not merge newly supplied seed keys into an existing row. An empty object `{}` or an unset variable uses normal defaults. Use a JSON object, not the API's `{"settings": {...}}` wrapper. Invalid JSON and non-object values are rejected during configuration loading. Timezone, entry-limit, lookback, and onboarding values use the existing settings validators during initialization.

Onboarding defaults to enabled. Set `PRE_SEED_SETTINGS='{"onboarding_enabled":false}'` to disable it during initialization; the value is copied to existing users. This replaces the removed `SKIP_INITIAL_USER_ONBOARDING` variable. After initialization, use Admin Settings to change values. Removing the variable does not undo persisted settings; no database migration is required.

### Bundled LLM inference

Deployment Compose stacks ship `ghcr.io/taranis-ai/gemma4-e4b-gguf:cpu` as the private `llm-inference` service, replacing standalone summary/clustering and `llm-bot` containers. The baked model alias is `unsloth/gemma-4-E4B-it-GGUF`; the endpoint is `http://llm-inference:8000/v1` using Chat Completions. The published CPU tag supports linux/amd64 and linux/arm64; Compose selects the host architecture automatically. Allow several minutes for loading and sufficient RAM for the model and 8192-token context. Kubernetes reserves 6 GiB and allows 12 GiB; tune this after measuring your workload. No GPU or model download at startup is needed.

Core automatically ensures the `internal` endpoint at `http://llm-inference:8000/v1` exists on fresh databases and every restart. Set `LLM_INFERENCE_API_KEY` in the private deployment environment; Compose passes it to Core and to inference as `LLAMA_API_KEY`. Core refreshes the stored key on every startup, including key rotation or clearing. A saved endpoint with the same URL is reused, preserving its model/API/timeout values. Existing default and feature/bot selections remain authoritative; internal is selected only when the shared default is empty. This is separate from `PRE_SEED_SETTINGS`, which only applies to fresh databases. `DEFAULT_LLM_ENDPOINT` overrides the internal endpoint object; explicit `{}` disables registration. Removing the variable uses the built-in service URL. Change other providers in **Admin Settings > LLM Endpoints**. Set `LLM_INFERENCE_IMAGE` to override the published image; update the endpoint model/API settings to match.

NER, sentiment, and cybersecurity classification also call this shared endpoint directly from workers. Their standalone containers are removed from the bots, PPN, and Tor Compose variations. Configure feature assignments or per-bot selections in LLM Endpoints; old service URLs and keys are unused. Classification uses each bot’s `CLASSIFICATION_THRESHOLD`.

After updating, pull images, restart services, and remove obsolete bot containers:

```bash
docker compose pull
docker compose up -d --remove-orphans
docker compose ps
```

Verify inference health, Core readiness, worker health, the selected default in Admin Settings, and known NER, sentiment, classification, summary, and clustering jobs. Keep the previous images and configuration for rollback. Restore the old bot services and their endpoints if reverting; no database schema migration is needed.

## Startup & Usage

Start-up application

For an existing PostgreSQL 14–17 installation, follow the [database upgrade procedure](#upgrade-the-bundled-postgresql-database-to-18) before starting the updated Compose stack; a normal startup would create an empty PostgreSQL 18 volume.

```bash
docker compose up -d
```

The `core` healthcheck runs every 5 minutes because it performs non-trivial service checks. Worker-related services (`collector`, `workers`, `cron`) use the packaged `taranis-worker-healthcheck` command for container health probes.

**Note:** If you have development environment variables set (e.g., from sourcing `dev/env.dev`), unset `TARANIS_CORE_URL` for the Docker command to avoid configuration conflicts:

```bash
env -u TARANIS_CORE_URL docker compose up -d
```

Use the application

```
http://<url>:<TARANIS_PORT>/login
```

### Upgrade the bundled PostgreSQL database to 18

The Compose database defaults to PostgreSQL 18. Its data lives in `database_data`, mounted at `/var/lib/postgresql`; the [official 18 image](https://hub.docker.com/_/postgres) stores the cluster below `/var/lib/postgresql/18/docker`. An existing PostgreSQL 14–17 `database_data` volume cannot be started with the 18 image.

Before upgrading, ensure `POSTGRES_TAG` is unset or set to `18-alpine`, allow enough free space for a full backup, and stop any clients that write directly to PostgreSQL. From the repository root, run:

```bash
./docker/database/upgrade-database.sh
```

The script confirms the running server version, pulls the 18 image, stops application writers, saves the core files and a logical database dump under `docker/backups/`, recreates the database volume and restores the dump, restarts the stack, and checks readiness and the server version. Keep that backup private: it contains application data.

## Public reports

Products published with a `TARANIS_PUBLISHER` preset are stored in the `core_data` volume under `/app/data/published-reports`. Their stable URL is `http://<url>:<TARANIS_PORT>/reports/<product-id>` and intentionally requires no authentication. Republishing a product replaces the file at the same URL.

## Development

See [dev Readme](/dev/README.md) for a quick way to get a development environment running.

## Release gate tests

Before tagging or publishing a release, run the release gate against the already published `:latest` images from `ghcr.io/taranis-ai`:

```bash
./docker/run_release_gate_tests.sh
```

The default gate runs the PostgreSQL TLS multiprocess smoke test and then the load test. To rerun one gate:

```bash
./docker/run_release_gate_tests.sh postgres-tls
./docker/run_release_gate_tests.sh load
```

The same gate is available as the manual GitHub Actions workflow `Release gate tests`. It does not build application images. It pulls `ghcr.io/taranis-ai/taranis-core:latest`, `ghcr.io/taranis-ai/taranis-frontend:latest`, `ghcr.io/taranis-ai/taranis-ingress:latest`, and `ghcr.io/taranis-ai/load-test:latest`.

Useful overrides:

```bash
DOCKER_IMAGE_NAMESPACE=ghcr.io/taranis-ai TARANIS_TAG=latest ./docker/run_release_gate_tests.sh
LOCUST_USERS=10 LOCUST_SPAWN_RATE=2 LOCUST_RUN_TIME=10m ./docker/run_release_gate_tests.sh load
```

The load gate seeds synthetic stories and reports before Locust starts. Failed Locust flows are reported but do not fail the release gate; setup and runner errors remain fatal. Load-test artifacts are written to `$LOAD_ARTIFACT_DIR` when set, otherwise to a temporary directory. The GitHub Actions workflow uploads those reports together with its captured release-gate output.

## PostgreSQL TLS multiprocess smoke test

To verify that the `core` service works with PostgreSQL TLS and multiple Granian workers:

```bash
./docker/test_core_postgres_tls_multiprocess.sh
```

The script pulls the configured `taranis-core` image, starts only `database`, `redis`, and `core`, requires PostgreSQL TLS, probes `/api/health`, checks for SSL worker failures, and cleans up its containers and volumes.

For Podman-compatible environments, use an existing image and pass the compose command explicitly if needed:

```bash
CONTAINER_CLI=podman COMPOSE_CMD="podman compose" ./docker/test_core_postgres_tls_multiprocess.sh
```

## Initial Setup 👤

**The default credentials are `user` / `user` and `admin` / `admin`.**

Open `http://<url>:<TARANIS_PORT>/config/sources` and click [Import] to import json-file with sources (see below)

## Advanced monitoring

Taranis AI supports Sentry monitoring in `core` and `frontend`, plus OpenTelemetry monitoring in `core`, `frontend`, and RQ workers. It uses
[OpenTelemetry Flask instrumentation](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/flask/flask.html) for the web services.
Set `OTEL_EXPORTER_OTLP_ENDPOINT` to one OTLP/HTTP base URL. Taranis sends traces to `/v1/traces` and metrics to `/v1/metrics`; leaving the base endpoint unset disables OpenTelemetry.

Every Compose configuration includes an optional [Grafana OpenTelemetry LGTM](https://grafana.com/docs/opentelemetry/docker-lgtm/) service. Start the application and the bundled telemetry stack with:

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://telemetry:4318 docker compose --profile telemetry up -d
```

Grafana and OTLP host ports bind to `127.0.0.1` only in every Compose configuration. For remote access, use an SSH tunnel. Before exposing Grafana through a reverse proxy or changing its binding, set a unique `GRAFANA_ADMIN_PASSWORD` and configure TLS and access controls. Keep the unauthenticated OTLP ports private. For an existing `telemetry_data` volume, change the password in Grafana; the environment variable only initializes new data.

Open Grafana at `http://localhost:${GRAFANA_PORT:-3000}` and sign in with `${GRAFANA_ADMIN_USER:-admin}` / `${GRAFANA_ADMIN_PASSWORD:-admin}`. The `telemetry_data` volume persists the local LGTM data. To use an external OTLP backend instead, omit the profile and set its base URL in `OTEL_EXPORTER_OTLP_ENDPOINT`.

Frontend HTTP client spans, core request spans, and RQ job spans share W3C trace context. Workers also export completed-job counts and job-duration histograms. `OTEL_METRIC_EXPORT_INTERVAL` is expressed in milliseconds and defaults to `60000`.

## Advanced build methods

### Individually build the containers

To build the Docker images individually, you need to clone the source code repository.

```bash
git clone https://github.com/taranis-ai/taranis-ai
```

Afterwards go to the cloned repository and launch the `docker build` command for the specific container image, like so:

```bash
cd Taranis AI
docker build -t taranis-core . -f ./docker/Containerfile.core
docker build -t taranis-ingress . -f ./docker/Containerfile.ingress
docker build -t taranis-worker . -f ./docker/Containerfile.worker
docker build -t taranis-frontend . -f ./docker/Containerfile.frontend
```

There are several Dockerfiles and each of them builds a different component of the system. These Dockerfiles exist:

- [Dockerfile.worker](Dockerfile.worker)
- [Dockerfile.core](Dockerfile.core)
- [Dockerfile.ingress](Dockerfile.ingress)
- [Dockerfile.frontend](Dockerfile.frontend)

# Configuration

## Container variables

### `database`

Any configuration options are available at [https://hub.docker.com/\_/postgres](https://hub.docker.com/_/postgres).

### `core`

Taranis Python clients use redis-py's default RESP3 protocol with maintenance notifications disabled. Redis Cloud and Redis Software Smart Client Handoffs are therefore not used; clients rely on their normal reconnect behavior during server maintenance.

| Environment variable          | Description                                | Default       |
| ----------------------------- | ------------------------------------------ | ------------- |
| `TARANIS_AUTHENTICATOR`       | Authentication method for users.           | `database`    |
| `REDIS_URL`                   | Redis connection URL                       | `redis://redis:6379` |
| `PRE_SEED_PASSWORD_ADMIN`     | Initial password for `admin`               | `admin`       |
| `PRE_SEED_PASSWORD_USER`      | Initial password for `user`                | `user`        |
| `PRE_SEED_SETTINGS`          | Flat JSON object for initial global settings | `{}`        |
| `API_KEY`                     | API Key for communication with workers     | `supersecret` |
| `DEBUG`                       | Debug logging                              | `False`       |
| `DB_URL`                      | PostgreSQL database URL                    | `localhost`   |
| `DB_DATABASE`                 | PostgreSQL database name                   | `taranis`     |
| `DB_USER`                     | PostgreSQL database user                   | `taranis`     |
| `DB_PASSWORD`                 | PostgreSQL database password               | `supersecret` |
| `JWT_SECRET_KEY`              | JWT token secret key.                      | `supersecret` |
| `JWT_COOKIE_SUFFIX`           | Literal suffix for JWT and CSRF cookie names | `''`        |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP/HTTP base URL for traces and metrics  | `''`          |
| `OTEL_EXPORTER_OTLP_HEADERS`  | Optional OTLP exporter headers             | `''`          |
| `OTEL_METRIC_EXPORT_INTERVAL` | Metric export interval in milliseconds     | `60000`       |
| `REALTIME_ENABLED`            | Enable Centrifugo publication and browser connections | `false` |
| `CENTRIFUGO_API_URL`          | Cluster-internal Centrifugo HTTP API URL   | `http://centrifugo:9000` |
| `CENTRIFUGO_API_KEY`          | Dedicated Centrifugo HTTP API key          | none          |
| `CENTRIFUGO_CONNECT_PROXY_SECRET` | Dedicated connect-proxy shared secret  | none          |
| `CENTRIFUGO_ALLOWED_ORIGINS`  | Space-separated exact browser origins     | `http://localhost:8080` |
| `TARANIS_CORE_SENTRY_DSN`     | Core Sentry DSN                            | `''`          |
| `TARANIS_BASE_PATH`           | Path under which Taranis AI is reachable   | `/`           |
| `GRANIAN_WORKERS_MAX_RSS`     | Per-worker Granian RSS recycle limit in MiB| `4096`        |
| `CHAT_ENABLED`                | Enable the optional analyst Chat API; configure the provider in Admin Settings > Chat | `false` |

The supplied Centrifugo configuration enables presence only for `global:events`, which every authenticated browser already receives. Core uses the server API to provide the `ADMIN_OPERATIONS`-protected connected-client snapshot on the Admin Notifications page; browsers are not granted presence access, and organization/user channel presence remains disabled.

`CENTRIFUGO_API_KEY` and `CENTRIFUGO_CONNECT_PROXY_SECRET` must be non-empty and distinct from each other, `API_KEY`, and `JWT_SECRET_KEY`.

The Centrifugo service also reads `CENTRIFUGO_REDIS_URL` directly; core does not. The sample environment derives its Redis URL password from `REDIS_PASSWORD` so the two credentials cannot drift.
All other Centrifugo server behavior is configured through native `CENTRIFUGO_*` environment variables; no configuration file or runtime config volume is required.

### `worker`

| Environment variable    | Description                                | Default                     |
| ----------------------- | ------------------------------------------ | --------------------------- |
| `TARANIS_CORE_URL`      | URL of the Taranis AI core API             | '' *                        |
| `TARANIS_BASE_PATH`     | Path under which Taranis AI is reachable   | `/`                         |
| `TARANIS_CORE_HOST`*    | Hostname and Port of the Taranis AI core   | `core:8080`                 |
| `API_KEY`               | API Key for communication with core        | `supersecret`               |
| `REDIS_URL`             | Redis connection URL                       | `redis://redis:6379`        |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP/HTTP base URL for job traces and metrics | `''`                  |
| `OTEL_EXPORTER_OTLP_HEADERS` | Optional OTLP exporter headers           | `''`                        |
| `OTEL_METRIC_EXPORT_INTERVAL` | Metric export interval in milliseconds   | `60000`                     |
| `DISABLE_HTTP3`         | Disable HTTP/3 for web-based collectors    | `False`                     |
| `DEBUG`                 | Debug logging                              | `False`                     |


### `frontend`

| Environment variable    | Description                                | Default                     |
| ----------------------- | ------------------------------------------ | --------------------------- |
| `JWT_SECRET_KEY`        | JWT token secret key.                      | `supersecret`               |
| `JWT_COOKIE_SUFFIX`     | Literal suffix for JWT and CSRF cookie names | `''`                      |
| `TARANIS_BASE_PATH`     | Deployment path used to scope authentication cookies | `/`              |
| `TARANIS_CORE_URL`      | URL of the Taranis AI core API             | '' *                        |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP/HTTP base URL for traces and metrics  | `''`                         |
| `OTEL_EXPORTER_OTLP_HEADERS` | Optional OTLP exporter headers              | `''`                         |
| `OTEL_METRIC_EXPORT_INTERVAL` | Metric export interval in milliseconds     | `60000`                      |
| `REALTIME_ENABLED`      | Open the authenticated same-origin EventSource | `false`                  |
| `TARANIS_FRONTEND_SENTRY_DSN` | Frontend Sentry DSN                        | `''`                         |
| `DEBUG`                 | Debug logging                              | `False`                     |
| `GRANIAN_WORKERS_MAX_RSS` | Per-worker Granian RSS recycle limit in MiB | `1024`       |
| `CHAT_ENABLED`            | Show the optional analyst Chat workspace    | `false`      |


> [!NOTE]
> ** If `TARANIS_CORE_URL` is not set it will be calculated as: `http://{TARANIS_CORE_HOST}/{TARANIS_BASE_PATH}/api`.
>
> If you set `TARANIS_CORE_URL`, `TARANIS_CORE_HOST` is ignored. `TARANIS_BASE_PATH` still scopes authentication cookies.

When multiple deployments share a domain, give each deployment a unique `JWT_COOKIE_SUFFIX` including its separator, such as `_q` for `TARANIS_BASE_PATH=/q/`. Core and frontend must receive the same suffix and base path. The access-token and CSRF cookies are also scoped to that base path.

With `DEBUG=false`, core and frontend require HTTPS browser access: JWT/CSRF and session cookies are Secure, and responses include HSTS and browser security headers. Dynamic responses use `Cache-Control: no-store`; static assets retain caching. Terminate TLS and redirect HTTP at your ingress. Keep DEBUG aligned between both services; the old `JWT_COOKIE_SECURE` override no longer disables Secure cookies. Use `DEBUG=true` only for isolated HTTP development.

### `ingress`

| Environment variable     | Description                                       | Default      |
| ------------------------ | ------------------------------------------------- | ------------ |
| `TARANIS_CORE_API`       | URL of the Taranis core API.                      | `/api/`      |
| `TARANIS_CORE_UPSTREAM`  | nginx upstream for the Taranis Core               | `core:8080`  |
| `NGINX_WORKERS`          | Number of nginx worker threads to spawn.          | `4`          |
| `NGINX_CONNECTIONS`      | Maximum number of connections per worker thread.  | `16`         |
| `TARANIS_BASE_PATH`      | Path under which Taranis AI is reachable          | `/`          |
