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
* deno
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

Start a tmux session with multiple panes for the different processes:

```bash
# Start a new session named taranis with the first tab and cd to src/core
tmux new-session -s taranis -n core -c src/core -d

# Create the second tab and cd to src/frontend
tmux new-window -t taranis:1 -n frontend -c src/frontend

# Create the third tab and cd to src/worker
tmux new-window -t taranis:2 -n worker -c src/worker

# Create the fourth tab for cron scheduler
tmux new-window -t taranis:3 -n cron -c src/worker

# Create the fifth tab for rq-dashboard (optional, for monitoring)
tmux new-window -t taranis:4 -n rq-dashboard -c src/worker

# Attach to the session
tmux attach-session -t taranis
```

Or simply run `./dev/start_tmux.sh` which sets up all windows automatically.

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
uv run python start_dev_worker.py
```

In Frontend Tab:
If `deno` is not available, check the [install guide](https://docs.deno.com/runtime/getting_started/installation/)

```bash
deno install --allow-scripts

# Watch and rebuild tailwindcss
deno task tw:watch

# Bundle vendor libraries
deno task vendor:bundle

# If venv isn't setup already
uv venv

# Activate venv
source .venv/bin/activate

# Install requirements
uv sync --upgrade --all-extras

# Run the frontend dev server
flask run
```

Taranis AI should be reachable on _local.taranis.ai_.

## Development Tools

### RQ Cron Scheduler

The development setup includes an **RQ Cron Scheduler** that automatically enqueues recurring jobs based on database schedules. It:

* Monitors OSINT sources and bots with cron schedules in the database
* Automatically enqueues collection and bot tasks at their scheduled times
* Dynamically updates when schedules change (reloads configuration)

When using `./dev/start_tmux.sh`, the cron scheduler is automatically started in window 4.

**Manual start:**
```bash
cd src/worker
uv sync --all-extras
uv run python start_cron_scheduler.py
```

**Updating schedules:**
When you update a source/bot schedule in the database (via the UI or API):
1. The change is immediately saved to the database
2. The cron scheduler will automatically reload and pick up the changes
3. For immediate updates during development, you can restart the cron scheduler window in tmux (Ctrl+b, then select window 4, Ctrl+C to stop, up arrow and Enter to restart)

### RQ Dashboard

The development setup includes [rq-dashboard](https://github.com/Parallels/rq-dashboard) for monitoring RQ workers and jobs. It provides:

* Real-time view of queues, workers, and jobs
* Job details including arguments, results, and tracebacks
* Ability to cancel jobs, requeue failed jobs, and empty queues

When using `./dev/start_tmux.sh`, rq-dashboard is automatically started on port **9181** in window 5.

Access it at: http://localhost:9181

**Manual start:**
```bash
cd src/worker
uv sync --all-extras
uv run rq-dashboard --redis-url redis://localhost:6379
```

## Technology stack

### Backend

* Python: Used for the core backend services including [REST API](../src/core/README.md).
* RQ (Redis Queue): For managing asynchronous tasks and [worker processes](../src/worker/README.md).

### Frontend

The frontend is served by the [Flask & HTMX REST frontend](../src/frontend/README.md).

### Support Services

* PostgreSQL: As the primary database.
* RabbitMQ: For message brokering and queue management.

### DevOps and Deployment

* Docker: For containerization.
* docker-compose: For managing multi-container Docker applications.
* Sentry: For error monitoring.
* CI/CD: GitHub Actions
