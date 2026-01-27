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

**Note:** If you have development environment variables set (e.g., from sourcing `dev/env.dev`), use the wrapper script instead to avoid configuration conflicts:

```bash
./compose.sh up -d
```

The wrapper script automatically unsets development environment variables that shouldn't affect Docker deployments.

Use the application

```
http://<url>:<TARANIS_PORT>/login
```

## Development

See [dev Readme](/dev/README.md) for a quick way to get a development environment running.

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
| `API_KEY`                     | API Key for communication with workers     | `supersecret` |
| `DEBUG`                       | Debug logging                              | `False`       |
| `DB_URL`                      | PostgreSQL database URL                    | `localhost`   |
| `DB_DATABASE`                 | PostgreSQL database name                   | `taranis`     |
| `DB_USER`                     | PostgreSQL database user                   | `taranis`     |
| `DB_PASSWORD`                 | PostgreSQL database password               | `supersecret` |
| `JWT_SECRET_KEY`              | JWT token secret key.                      | `supersecret` |
| `TARANIS_CORE_SENTRY_DSN`     | DSN address for Sentry; includes DB as well| ''            |
| `TARANIS_BASE_PATH`           | Path under which Taranis AI is reachable   | `/`           |

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
| `TARANIS_CORE_URL`      | URL of the Taranis AI core API             | '' *                        |
| `DEBUG`                 | Debug logging                              | `False`                     |


> [!NOTE]
> ** If `TARANIS_CORE_URL` is not set it will be calculated as: `http://{TARANIS_CORE_HOST}/{TARANIS_BASE_PATH}/api`.
>
> If you set `TARANIS_CORE_URL`: `TARANIS_CORE_HOST` and `TARANIS_BASE_PATH` will be ignored.

### `ingress`

| Environment variable     | Description                                       | Default      |
| ------------------------ | ------------------------------------------------- | ------------ |
| `TARANIS_CORE_API`       | URL of the Taranis core API.                      | `/api/`      |
| `TARANIS_CORE_UPSTREAM`  | nginx upstream for the Taranis Core               | `core:8080`  |
| `NGINX_WORKERS`          | Number of nginx worker threads to spawn.          | `4`          |
| `NGINX_CONNECTIONS`      | Maximum number of connections per worker thread.  | `16`         |
| `TARANIS_BASE_PATH`      | Path under which Taranis AI is reachable          | `/`          |
