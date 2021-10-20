# Taranis NG Docker images

Taranis NG supports deployment in Docker containers. This repository also contains an example [docker-compose.yml](docker-compose.yml) file which runs the whole application in one stack.

This folder contains additional support files for the creation of the Docker containers. These include start and pre-start scripts, the application entrypoint, and the [gunicorn](https://gunicorn.org/) configuration file.

## Prerequisites

- [Docker](https://docs.docker.com/engine/install/)
- [Docker-compose](https://docs.docker.com/compose/install/) >= 1.27.0
- (Optional) [Vim](https://www.vim.org/) or other text editor - for configuration and development

## Quickly build and run Taranis NG using [docker-compose](docker-compose.yml)

_First_, you need to clone this repository:

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

or, alternatively, build and run the containers with:

```bash
docker-compose -f docker/docker-compose.yml up --build
```

**Voila, Taranis NG is up and running. Visit your instance by navigating to [http://127.0.0.1:8080/](http://127.0.0.1:8080/) using your web browser**.

Your Taranis NG instance now needs to be configured.
Continue [here](../README.md#connecting-to-collectors-presenters-and-publishers).

<hr />

To import the [sample data](../src/core/scripts/sample_data.py) and create basic user accounts, set the environment variable `TARANIS_NG_SAMPLE_DATA` for the core container to `true`, or import sample data using the [management script](#management-script-how-to) (from another terminal):

```bash
docker exec -it taranis-ng_core_1 python manage.py sample-data
```

*<u>Note:</u> the container name `taranis-ng_core_1` was automatically generated when running the example [docker-compose.yml](docker-compose.yml) file without any changes. To get the exact container name for the core component of your instance, use `docker ps`.*

<hr />

**The default credentials are `user` / `user` and `admin` / `admin`.**

## Advanced build methods

### Individually build the containers

To build the Docker images individually, you need to clone this repository.

```bash
git clone https://github.com/SK-CERT/Taranis-NG.git
```

Afterwards go to the cloned repository and launch the `docker build` command for the specific container image, like so:

```bash
cd Taranis-NG
docker build -t taranis-ng-bots . -f ./docker/Dockerfile.bots
docker build -t taranis-ng-collectors . -f ./docker/Dockerfile.collectors
docker build -t taranis-ng-core . -f ./docker/Dockerfile.core
docker build -t taranis-ng-gui . -f ./docker/Dockerfile.gui
docker build -t taranis-ng-presenters . -f ./docker/Dockerfile.presenters
docker build -t taranis-ng-publishers . -f ./docker/Dockerfile.publishers
```

There are several Dockerfiles and each of them builds a different component of the system. These Dockerfiles exist:

- [Dockerfile.bots](Dockerfile.bots)
- [Dockerfile.collectors](Dockerfile.collectors)
- [Dockerfile.core](Dockerfile.core)
- [Dockerfile.gui](Dockerfile.gui)
- [Dockerfile.presenters](Dockerfile.presenters)
- [Dockerfile.publishers](Dockerfile.publishers)

## Configuration

### Docker configuration

#### `redis`
Any configuration options are available at [https://hub.docker.com/_/redis](https://hub.docker.com/_/redis).

#### `database`
Any configuration options are available at [https://hub.docker.com/_/postgres](https://hub.docker.com/_/postgres).

#### `core`

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
| `TARANIS_NG_SAMPLE_DATA`    | To install sample data, set to `"true"`.<br /> When this option is enabled, the user account specified in the variables below won't be automatically created. | `false` |
| `TARANIS_NG_ADMIN_USERNAME`     | To automatically create a full-priviledge role and an administrator account, set to some username, like `"admin"`. | `john.doe` |
| `TARANIS_NG_ADMIN_PASSWORD` | Set a password for the automatically created user account. If no password is specified, one will be generated. | `password1` |

Taranis NG can use [connection pooling](https://docs.sqlalchemy.org/en/14/core/pooling.html) to maintain multiple active connections to the database server. Connection pooling is required when your deployment serves hundreds of customers from one instance. To enable connection pooling, set the `DB_POOL_SIZE`, `DB_POOL_RECYCLE`, and `DB_POOL_TIMEOUT` environment variables.

#### `bots`, `collectors`, `presenters`, `publishers`

| Environment variable        | Description | Example |
|-----------------------------|-------------|----------|
| `TARANIS_NG_CORE_URL`       | URL of the Taranis NG core API. | `http://127.0.0.1:8080/api/v1` |
| `API_KEY`                   | Shared API key. | `cuBG/4H9lGTeo47F9X6DUg` |
| `WORKERS_PER_CORE`          | Number of gunicorn worker threads to spawn per CPU core. | `4` |

#### `gui`

| Environment variable          | Description | Example |
|-------------------------------|-------------|----------|
| `VUE_APP_TARANIS_NG_CORE_API` | URL of the Taranis NG core API. | `http://127.0.0.1:8080/api/v1` |
| `VUE_APP_TARANIS_NG_CORE_SSE` | URL of the Taranis NG SSE endpoint. | `http://127.0.0.1:8080/sse` |
| `VUE_APP_TARANIS_NG_URL`      | URL of the Taranis NG frontend. | `http://127.0.0.1` |
| `VUE_APP_TARANIS_NG_LOCALE`   | Application locale. | `en` |
| `NGINX_WORKERS`               | Number of NginX worker threads to spawn. | `4` |
| `NGINX_CONNECTIONS`           | Maximum number of allowed connections per one worker thread. | `16` |

### Management script how-to

Taranis NG core container comes with a simple management script that may be used to set up and configure the instance without manual interaction with the database.

To run the management script, launch a shell inside of the docker container for the core component with this command:

```bash
docker exec -it [CONTAINER] python manage.py [COMMAND] [PARAMETERS]
```

Currently, you may manage the following:

| Command     | Description | Parameters |
|-------------|-------------|------------|
| `sample-data` | Install sample data with basic configuration.<br />*This is for show-case and testing purposes only.* | N/A |
| `account`     | (WIP) List, create, edit and delete user accounts. | `--list`, `-l` : list all user accounts<br /> `--create`, `-c` : create a new user account<br /> `--edit`, `-e` : edit an existing user account<br /> `--delete`, `-d` : delete a user account<br /> `--username` : specify the username<br /> `--name` : specify the user's name<br /> `--password` : specify the user's password<br /> `--roles` : specify a list of roles, divided by a comma (`,`), that the user belongs to |
| `role`     | (WIP) List, create, edit and delete user roles. | `--list`, `-l` : list all roles<br /> `--filter`, `-f` : filter roles by their name or description<br /> `--create`, `-c` : create a new role<br /> `--edit`, `-e` : edit an existing role<br /> `--delete`, `-d` : delete a role<br /> `--id` : specify the role id (in combination with `--edit` or `--delete`)<br /> `--name` : specify the role name<br /> `--description` : specify the role description (default is `""`)<br /> `--permissions` : specify a list of permissions, divided with a comma (`,`), that the role would allow |
| `dictionary`     | Update CPE and CVE dictionaries. | `--upload-cpe` : upload the CPE dictionary (expected on STDIN in XML format) to the path indicated by `CPE_UPDATE_FILE` environment variable, and update the database from that file.<br /> `--upload-cve` : upload the CVE dictionary (expected on STDIN in XML format) to the path indicated by `CVE_UPDATE_FILE`, and update the database from that file |


#### Example usage

##### Install sample data

```bash
python manage.py sample-data
```

Command output:

```
Installing sample data...
Tables created.
Sample data installed.
```

##### Create a new role with a set of permissions

```bash
python manage.py role \
    --create \
    --name "Custom role 1" \
    --description "Custom role with analysis and assessment access" \
    --permissions "ANALYZE_ACCESS, ANALYZE_CREATE, ANALYZE_UPDATE, \
    ANALYZE_DELETE, ASSESS_ACCESS, ASSESS_CREATE, ASSESS_UPDATE, \
    ASSESS_DELETE, MY_ASSETS_ACCESS, MY_ASSETS_CREATE, MY_ASSETS_CONFIG"
```

Command output:

```
Role 'Custom role 1' with id 3 created.
```

##### Role filter

```bash
python manage.py role \
    --list \
    --filter "Custom role 1"
```

Command output:

```
Id: 3
	Name: Custom role 1
	Description: Custom role with analysis and assessment access
	Permissions: ['ANALYZE_ACCESS', 'ANALYZE_CREATE', 'ANALYZE_UPDATE', 'ANALYZE_DELETE', 'ASSESS_ACCESS', 'ASSESS_CREATE', 'ASSESS_UPDATE', 'ASSESS_DELETE', 'MY_ASSETS_ACCESS', 'MY_ASSETS_CREATE', 'MY_ASSETS_CONFIG']
```

##### Create a new user account

```bash
python manage.py account \
    --create \
    --name "John Doe" \
    --username "test_user" \
    --password "supersecret" \
    --roles 3
```

Command output:

```
User 'test_user' created.
```

##### Upload a CPE dictionary

```bash
gzcat official-cpe-dictionary_v2.3.xml.gz | python manage.py dictionary --upload-cpe
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
