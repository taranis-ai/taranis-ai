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

## Startup & Usage

Start-up application

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

Taranis AI supports advanced monitoring of `ingress`, `core` and `database` using [Sentry](https://docs.sentry.io/). It can be enabled by setting respective `SENTRY_DSN` environment variables described below.

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

| Environment variable          | Description                                | Default       |
| ----------------------------- | ------------------------------------------ | ------------- |
| `TARANIS_AUTHENTICATOR`       | Authentication method for users.           | `database`    |
| `REDIS_URL`                   | Redis connection URL                       | `redis://redis:6379` |
| `PRE_SEED_PASSWORD_ADMIN`     | Initial password for `admin`               | `admin`       |
| `PRE_SEED_PASSWORD_USER`      | Initial password for `user`                | `user`        |
| `SKIP_INITIAL_USER_ONBOARDING`| Initially disable onboarding for all users | `False`       |
| `API_KEY`                     | API Key for communication with workers     | `supersecret` |
| `DEBUG`                       | Debug logging                              | `False`       |
| `DB_URL`                      | PostgreSQL database URL                    | `localhost`   |
| `DB_DATABASE`                 | PostgreSQL database name                   | `taranis`     |
| `DB_USER`                     | PostgreSQL database user                   | `taranis`     |
| `DB_PASSWORD`                 | PostgreSQL database password               | `supersecret` |
| `JWT_SECRET_KEY`              | JWT token secret key.                      | `supersecret` |
| `JWT_COOKIE_SUFFIX`           | Literal suffix for JWT and CSRF cookie names | `''`        |
| `TARANIS_CORE_SENTRY_DSN`     | DSN address for Sentry; includes DB as well| ''            |
| `TARANIS_BASE_PATH`           | Path under which Taranis AI is reachable   | `/`           |
| `GRANIAN_WORKERS_MAX_RSS`     | Per-worker Granian RSS recycle limit in MiB| `4096`        |

### `worker`

| Environment variable    | Description                                | Default                     |
| ----------------------- | ------------------------------------------ | --------------------------- |
| `TARANIS_CORE_URL`      | URL of the Taranis AI core API             | '' *                        |
| `TARANIS_BASE_PATH`     | Path under which Taranis AI is reachable   | `/`                         |
| `TARANIS_CORE_HOST`*    | Hostname and Port of the Taranis AI core   | `core:8080`                 |
| `API_KEY`               | API Key for communication with core        | `supersecret`               |
| `REDIS_URL`             | Redis connection URL                       | `redis://redis:6379`        |
| `DEBUG`                 | Debug logging                              | `False`                     |


### `frontend`

| Environment variable    | Description                                | Default                     |
| ----------------------- | ------------------------------------------ | --------------------------- |
| `JWT_SECRET_KEY`        | JWT token secret key.                      | `supersecret`               |
| `JWT_COOKIE_SUFFIX`     | Literal suffix for JWT and CSRF cookie names | `''`                      |
| `TARANIS_BASE_PATH`     | Deployment path used to scope authentication cookies | `/`              |
| `TARANIS_CORE_URL`      | URL of the Taranis AI core API             | '' *                        |
| `DEBUG`                 | Debug logging                              | `False`                     |
| `GRANIAN_WORKERS_MAX_RSS` | Per-worker Granian RSS recycle limit in MiB | `1024`       |


> [!NOTE]
> ** If `TARANIS_CORE_URL` is not set it will be calculated as: `http://{TARANIS_CORE_HOST}/{TARANIS_BASE_PATH}/api`.
>
> If you set `TARANIS_CORE_URL`, `TARANIS_CORE_HOST` is ignored. `TARANIS_BASE_PATH` still scopes authentication cookies.

When multiple deployments share a domain, give each deployment a unique `JWT_COOKIE_SUFFIX` including its separator, such as `_q` for `TARANIS_BASE_PATH=/q/`. Core and frontend must receive the same suffix and base path. The access-token and CSRF cookies are also scoped to that base path.

### `ingress`

| Environment variable     | Description                                       | Default      |
| ------------------------ | ------------------------------------------------- | ------------ |
| `TARANIS_CORE_API`       | URL of the Taranis core API.                      | `/api/`      |
| `TARANIS_CORE_UPSTREAM`  | nginx upstream for the Taranis Core               | `core:8080`  |
| `NGINX_WORKERS`          | Number of nginx worker threads to spawn.          | `4`          |
| `NGINX_CONNECTIONS`      | Maximum number of connections per worker thread.  | `16`         |
| `TARANIS_BASE_PATH`      | Path under which Taranis AI is reachable          | `/`          |
