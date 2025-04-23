# Taranis AI Development setup

## Easy Mode

Clone Repository

```bash
git clone git@github.com:taranis-ai/taranis-ai.git
cd taranis-ai
```


Copy env.dev to worker and core

```bash
cp dev/env.dev src/core/.env
cp dev/env.dev src/worker/.env
```

```bash
./dev/start_dev.sh
```

## Hard Mode

Install pre dependencies:

* git
* tmux
* nodejs >= 22
* build-essential
* [podman](https://podman.io/docs/installation) or [docker](https://docs.docker.com/engine/install/)

If using docker make sure to allow running it as [non-root user](https://docs.docker.com/engine/install/linux-postinstall/)
if using podman make sure to also install `podman-compose` and `podman-docker`

Starting from the git root:

```bash
cd $(git rev-parse --show-toplevel)
```

Copy env.dev to worker and core

```bash
cp dev/env.dev src/core/.env
cp dev/env.dev src/worker/.env
```

Copy env.sample to frontend
```bash
cp src/frontend/env.sample src/frontend/.env
```

Create a correct `config.local.json` file for gui

```bash
echo -e "{\n  \"TARANIS_CORE_API\": \"${TARANIS_CORE_URL}\"\n}" > src/gui/public/config.local.json
```

Start support services via the dev compose file

```bash
docker compose -f dev/compose.yml up -d
```

Setup nginx.
Make sure the paths are correct. Some distributions use a different nginx configuration directory hierarchy and rely on `.conf` suffix.
```bash
# Debian based example
sudo cp dev/nginx.conf /etc/nginx/sites-available/local.taranis.ai
sudo ln -s /etc/nginx/sites-available/local.taranis.ai /etc/nginx/sites-enabled/local.taranis.ai
sudo nginx -t && sudo systemctl restart nginx

# Red Hat based example
sudo cp dev/nginx.conf /etc/nginx/conf.d/local.taranis.ai.conf
sudo nginx -t && sudo systemctl restart nginx
```

Start a tmux session with 3 panes for the 3 processes:
```bash
# Start a new session named taranis with the first tab and cd to src/core
tmux new-session -s taranis -n core -c src/core -d

# Create the second tab and cd to src/gui
tmux new-window -t taranis:1 -n gui -c src/gui

# Create the third tab and cd to src/worker
tmux new-window -t taranis:2 -n worker -c src/worker

# Attach to the session
tmux attach-session -t taranis
```

In Core Tab:

```bash
# If venv isn't setup already
uv venv

# Activate venv
source .venv/bin/activate

# Install requirements
uv sync --upgrade --all-extras

# Run core
flask run
```

In Worker Tab:

```bash
# If venv isn't setup already
uv venv

# Activate venv
source .venv/bin/activate

# Install requirements
uv sync --upgrade --all-extras

# Run worker
celery -A worker worker
```

In GUI Tab:
If `pnpm` is not available, check the [install guide](https://pnpm.io/installation)

```bash
# If pnpm isn't setup already
npm install --global corepack@latest
corepack enable pnpm

# If node_modules isn't setup already
pnpm install

# Run GUI
pnpm run dev
```

Taranis AI should be reachable on _local.taranis.ai_.


## Technology stack

### Backend

* Python: Used for the core backend services including [REST API](../src/core/README.md).
* Celery: For managing asynchronous tasks and [worker processes](../src/worker/README.md).

### Frontend

The admininstration part is served by the [Flask & HTMX REST frontend](../src/frontend/README.md).

The assess & analyze part is served by the [vuejs frontend](../src/gui/README.md).

### Support Services

* PostgreSQL: As the primary database.
* RabbitMQ: For message brokering and queue management.

### DevOps and Deployment

* Docker: For containerization.
* docker-compose: For managing multi-container Docker applications.
* Sentry: For error monitoring.
* CI/CD: GitHub Actions
