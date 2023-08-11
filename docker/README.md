# Quick project reference

- Source code: [github.com/SK-CERT/Taranis-NG](https://github.com/SK-CERT/Taranis-NG)
- Docker images: [hub.docker.com/u/skcert](https://hub.docker.com/u/skcert)
- Maintained by: [SK-CERT](https://www.sk-cert.sk)
- Project web page: [taranis.ng](https://taranis.ng)
- Where to file issues (no vulnerability reports please): [GitHub issues page](https://github.com/SK-CERT/Taranis-NG/issues)
- Where to send security issues and vulnerability reports: [incident@nbu.gov.sk](mailto:incident@nbu.gov.sk)

## About Taranis NG

Taranis NG is an OSINT gathering and analysis tool for CSIRT teams and
organisations. It allows osint gathering, analysis and reporting; team-to-team
collaboration; and contains a user portal for simple self asset management.

Taranis crawls various **data sources** such as web sites or tweets to gather
unstructured **news items**. These are processed by analysts to create
structured **report items**, which are used to create **products** such as PDF
files, which are finally **published**.

Taranis supports **team-to-team collaboration**, and includes a light weight
**self service asset management** which automatically links to the advisories
that mention vulnerabilities in the software.

# Deploying Taranis NG with docker-compose

Taranis NG supports deployment in Docker containers. [The docker/ folder on
GitHub repository](https://github.com/SK-CERT/Taranis-NG/tree/main/docker)
contains a sample
[docker-compose.yml](https://raw.githubusercontent.com/SK-CERT/Taranis-NG/main/docker/docker-compose.yml)
file which runs the whole application in one stack.

The same folder also contains additional support files for the creation of the
Docker containers. These include start and pre-start scripts, the application
entrypoint, and the [gunicorn](https://gunicorn.org/) configuration file.

## Prerequisites

- [Docker](https://docs.docker.com/engine/install/)
- [docker-compose](https://docs.docker.com/compose/install/) >= 1.27.0
- (Optional) [Vim](https://www.vim.org/) or other text editor - for configuration and development

Please note it is important to use the abovementioned version of
`docker-compose` or newer, otherwise the build and deploy will fail.

## Quickly build and run Taranis NG using `docker-compose`

_First_, you need to clone the source code repository:

```bash
git clone https://github.com/SK-CERT/Taranis-NG.git
cd Taranis-NG
```

_Then_, using your favorite text editor, please change the default passwords in `docker/.env` file. You can only skip this step when deploying a non-production testing environment.

```bash
vim docker/.env
```

*_Optionally:_ you may modify other settings in the `docker/.env` and `docker/docker-compose.yml` files to your liking.  More information on container configuration can be found [here](#configuration).*

_Finally_, either deploy the ready-made images from Docker hub with:

```bash
docker-compose -f docker/docker-compose.yml pull
docker-compose -f docker/docker-compose.yml up --no-build
```

**The default credentials are `user` / `user` and `admin` / `admin`.**


## Advanced build methods

### Individually build the containers

To build the Docker images individually, you need to clone the source code repository.

```bash
git clone https://github.com/ait-cs-IaaS/Taranis-NG.git
```

Afterwards go to the cloned repository and launch the `docker build` command for the specific container image, like so:

```bash
cd Taranis-NG
docker build -t taranis-ng-core . -f ./docker/Dockerfile.core
docker build -t taranis-ng-gui . -f ./docker/Dockerfile.gui
docker build -t taranis-ng-worker . -f ./docker/Dockerfile.worker
```

There are several Dockerfiles and each of them builds a different component of the system. These Dockerfiles exist:

- [Dockerfile.worker](Dockerfile.worker)
- [Dockerfile.core](Dockerfile.core)
- [Dockerfile.gui](Dockerfile.gui)

# Configuration

## Container variables

### `rabbitmq`
Any configuration options are available at [https://hub.docker.com/_/redis](https://hub.docker.com/_/redis).

### `database`
Any configuration options are available at [https://hub.docker.com/_/postgres](https://hub.docker.com/_/postgres).

### `core`

| Environment variable        | Description | Example |
|-----------------------------|-------------|----------|
| `REDIS_URL`                 | Redis database URL. Used for SSE events. | `redis://redis` |
| `DB_URL`                    | PostgreSQL database URL. | `127.0.0.1` |
| `DB_DATABASE`               | PostgreSQL database name. | `taranis-ng` |
| `DB_USER`                   | PostgreSQL database user. | `taranis-ng` |
| `DB_PASSWORD`               | PostgreSQL database password. | `supersecret` |
| `DB_POOL_SIZE`              | SQLAlchemy QueuePool number of active connections to the database. | `100` |
| `DB_POOL_RECYCLE`           | SQLAlchemy QueuePool maximum connection age. | `300` |
| `DB_POOL_TIMEOUT`           | SQLAlchemy QueuePool connection timeout. | `5` |
| `JWT_SECRET_KEY`            | JWT token secret key. | `J6flTliJ076zWg` |
| `OPENID_LOGOUT_URL`         | Keycloak logout URL. | `https://example.com/auth/realms/master/protocol/openid-connect/logout` |
| `WORKERS_PER_CORE`          | Number of gunicorn worker threads to spawn per CPU core. | `4` |
| `SKIP_DEFAULT_COLLECTOR`    | Set to `true` to prevent initialization of a default docker collector at first run | `` |

Taranis NG can use [connection pooling](https://docs.sqlalchemy.org/en/14/core/pooling.html) to maintain multiple active connections to the database server. Connection pooling is required when your deployment serves hundreds of customers from one instance. To enable connection pooling, set the `DB_POOL_SIZE`, `DB_POOL_RECYCLE`, and `DB_POOL_TIMEOUT` environment variables.

### `worker`, `beat`

| Environment variable        | Description | Example |
|-----------------------------|-------------|----------|
| `TARANIS_NG_CORE_URL`       | URL of the Taranis NG core API. | `http://127.0.0.1:8080/api/v1` |
| `API_KEY`                   | Shared API key. | `cuBG/4H9lGTeo47F9X6DUg` |
| `WORKERS_PER_CORE`          | Number of gunicorn worker threads to spawn per CPU core. | `4` |

### `gui`

| Environment variable          | Description | Example |
|-------------------------------|-------------|----------|
| `TARANIS_NG_CORE_API` | URL of the Taranis NG core API. | `/api/` |
| `TARANIS_NG_CORE_UPSTREAM` | Nginx upstream for the Taranis-NG Core | `core` |
| `TARANIS_NG_SENTRY_DSN`    | Sentry DSN | '' |
| `NGINX_WORKERS`               | Number of NginX worker threads to spawn. | `4` |
| `NGINX_CONNECTIONS`           | Maximum number of allowed connections per one worker thread. | `16` |


#### Example usage


##### Upload a CPE dictionary

```bash
zcat official-cpe-dictionary_v2.3.xml.gz | manage.py dictionary --upload-cpe
```

Command output:

```
Processed CPE items: 1000
Processed CPE items: 2000
...
...
Processed CPE items: 789000
Processed CPE items: 789704
Dictionary was uploaded.
```
