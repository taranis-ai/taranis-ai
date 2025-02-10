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
dev/start_dev.sh
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

Start support services via the dev compose file

```bash
docker compose -f dev/compose.yml up -d
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

```bash
# If node modules isn't setup already
npm install

# Run GUI
pnpm run dev
```

## Optionally start scheduler (another repository) in tmux

```bash
cd ../taranis-scheduler # your taranis-scheduler directory
start_dev.sh
```


## Technology stack

### Backend

* Python: Used for the core backend services including REST API.
* Celery: For managing asynchronous tasks and worker processes.

### Frontend

* Vue.js: As the primary frontend framework.
* Vuetify: As a UI library for Vue.js.
* Vite: For the frontend build tool and development server.

### Support Services

* PostgreSQL: As the primary database.
* RabbitMQ: For message brokering and queue management.

### DevOps and Deployment

* Docker: For containerization.
* docker-compose: For managing multi-container Docker applications.
* Sentry: For error monitoring.
* CI/CD: GitHub Actions
