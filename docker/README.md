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
```
docker compose up -d
```

Use the application
```
http://<url>:<TARANIS_PORT>/login
```

## Development

See [dev Readme](/dev/README.md) for a quick way to get a development environment running.

## Initial Setup 👤

**The default credentials are `user` / `user` and `admin` / `admin`.**

Open `http://<url>:<TARANIS_PORT>/config/sources` and click [Import] to import json-file with sources (see below)


## Advanced build methods

### Individually build the containers

To build the Docker images individually, you need to clone the source code repository.

```bash
git clone https://github.com/taranis-ai/taranis-ai
```

Afterwards go to the cloned repository and launch the `docker build` command for the specific container image, like so:

```bash
cd Taranis AI
docker build -t taranis-core . -f ./docker/Dockerfile.core
docker build -t taranis-gui . -f ./docker/Dockerfile.gui
docker build -t taranis-worker . -f ./docker/Dockerfile.worker
```

There are several Dockerfiles and each of them builds a different component of the system. These Dockerfiles exist:

- [Dockerfile.worker](Dockerfile.worker)
- [Dockerfile.core](Dockerfile.core)
- [Dockerfile.gui](Dockerfile.gui)

# Configuration

## Container variables

### `rabbitmq`
Any configuration options are available at [https://hub.docker.com/_/rabbitmq](https://hub.docker.com/_/rabbitmq).

### `database`
Any configuration options are available at [https://hub.docker.com/_/postgres](https://hub.docker.com/_/postgres).

### `core`

| Environment variable        | Description | Example |
|-----------------------------|-------------|----------|
| `TARANIS_AUTHENTICATOR`  | Authentication method for users. | `database` |
| `QUEUE_BROKER_HOST`         | RabbitMQ Host address | `rabbitmq` |
| `QUEUE_BROKER_USER`         | RabbitMQ user | `taranis` |
| `QUEUE_BROKER_PASSWORD`     | RabbitMQ password | `supersecret` |
| `PRE_SEED_PASSWORD_ADMIN`   | Initial password for `admin` | `admin` |
| `PRE_SEED_PASSWORD_USER`    | Initial password for `user` | `user` |
| `API_KEY`                   | API Key for communication with workers | `supersecret` |
| `DEBUG`                     | Debug logging | `True` |
| `DB_URL`                    | PostgreSQL database URL. | `127.0.0.1` |
| `DB_DATABASE`               | PostgreSQL database name. | `taranis` |
| `DB_USER`                   | PostgreSQL database user. | `taranis` |
| `DB_PASSWORD`               | PostgreSQL database password. | `supersecret` |
| `DB_POOL_SIZE`              | SQLAlchemy QueuePool number of active connections to the database. | `100` |
| `DB_POOL_RECYCLE`           | SQLAlchemy QueuePool maximum connection age. | `300` |
| `DB_POOL_TIMEOUT`           | SQLAlchemy QueuePool connection timeout. | `5` |
| `JWT_SECRET_KEY`            | JWT token secret key. | `supersecret` |
| `WORKERS_PER_CORE`          | Number of gunicorn worker threads to spawn per CPU core. | `4` |


### `worker`, `beat`

| Environment variable        | Description | Example |
|-----------------------------|-------------|----------|
| `TARANIS_CORE_URL`          | URL of the Taranis NG core API. | `http://127.0.0.1:8080/api` |
| `API_KEY`                   | Shared API key. | `supersecret` |
| `QUEUE_BROKER_HOST`         | RabbitMQ Host address | `rabbitmq` |
| `QUEUE_BROKER_USER`         | RabbitMQ user | `taranis` |
| `QUEUE_BROKER_PASSWORD`     | RabbitMQ password | `supersecret` |
| `DEBUG`                     | Debug logging | `True` |


### `gui`

| Environment variable          | Description | Example |
|-------------------------------|-------------|----------|
| `TARANIS_CORE_API`      | URL of the Taranis core API. | `/api/` |
| `TARANIS_CORE_UPSTREAM` | nginx upstream for the Taranis Core | `core` |
| `TARANIS_SENTRY_DSN`    | Sentry DSN | '' |
| `NGINX_WORKERS`         | Number of nginx worker threads to spawn. | `4` |
| `NGINX_CONNECTIONS`     | Maximum number of allowed connections per one worker thread. | `16` |
