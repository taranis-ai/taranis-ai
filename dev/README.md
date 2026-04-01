# Taranis AI Development setup

Dependency updates use [Renovate](https://docs.renovatebot.com/) with [`.github/renovate.json`](../.github/renovate.json).

## Easy Mode

Clone the repository, then set up the local hostname and nginx reverse proxy before starting the automated workflow.

### Ubuntu proxy prerequisites

```bash
echo "127.0.0.1 local.taranis.ai" | sudo tee -a /etc/hosts
```

```bash
# Debian based example
sudo cp dev/nginx.conf /etc/nginx/sites-available/local.taranis.ai
sudo ln -sf /etc/nginx/sites-available/local.taranis.ai /etc/nginx/sites-enabled/local.taranis.ai
sudo nginx -t && sudo systemctl restart nginx

# Red Hat based example
sudo cp dev/nginx.conf /etc/nginx/conf.d/local.taranis.ai.conf
sudo nginx -t && sudo systemctl restart nginx
```

### macOS proxy prerequisites

Install Homebrew and Xcode Command Line Tools first, then add the local hostname:

```bash
echo "127.0.0.1 local.taranis.ai" | sudo tee -a /etc/hosts
```

Install Homebrew nginx and place the development config into the included `servers/` directory:

```bash
brew install nginx
mkdir -p "$(brew --prefix)/etc/nginx/servers"
cp dev/nginx.conf "$(brew --prefix)/etc/nginx/servers/local.taranis.ai.conf"
sudo ./dev/manage_macos_nginx.sh
```

Then start everything with:

```bash
./dev/start_dev.sh
```

`./dev/start_dev.sh` installs supported local dependencies, creates missing `.env` files, verifies Docker and proxy prerequisites, starts the compose services, and opens the tmux session.

## Hard Mode

Install pre dependencies:

* git
* tmux
* deno
* build-essential
* [docker](https://docs.docker.com/engine/install/) or another Docker-compatible daemon that provides `docker compose`

If using docker make sure to allow running it as a [non-root user](https://docs.docker.com/engine/install/linux-postinstall/)

Starting from the git root:

```bash
cd $(git rev-parse --show-toplevel)
```

Copy `env.dev` to the app directories:

```bash
cp dev/env.dev src/core/.env
echo "FLASK_RUN_PORT=5001" >> src/core/.env
cp dev/env.dev src/worker/.env
cp dev/env.dev src/frontend/.env
echo "FLASK_RUN_PORT=5002" >> src/frontend/.env
```

Setup nginx.
Make sure the paths are correct. Some distributions use a different nginx configuration directory hierarchy and rely on `.conf` suffix.

```bash
# Debian based example
sudo cp dev/nginx.conf /etc/nginx/sites-available/local.taranis.ai
sudo ln -sf /etc/nginx/sites-available/local.taranis.ai /etc/nginx/sites-enabled/local.taranis.ai
sudo nginx -t && sudo systemctl restart nginx

# Red Hat based example
sudo cp dev/nginx.conf /etc/nginx/conf.d/local.taranis.ai.conf
sudo nginx -t && sudo systemctl restart nginx
```

Start support services via the dev compose file:

```bash
docker compose -f dev/compose.yml up -d
```

Start a tmux session with 3 windows for the 3 processes:

```bash
# Start a new session named taranis with the first tab and cd to src/core
tmux new-session -s taranis -n core -c src/core -d

# Create the second tab and cd to src/frontend
tmux new-window -t taranis:1 -n frontend -c src/frontend

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

In Frontend Tab:

```bash
# If venv isn't setup already
uv venv

# Activate venv
source .venv/bin/activate

# Install requirements
uv sync --upgrade --all-extras

# Run the frontend dev server
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

In Tailwind Tab:

```bash
deno install --allow-scripts

# Watch and rebuild tailwindcss
deno task tw:watch

# Bundle vendor libraries
deno task vendor:bundle
```

Taranis AI should be reachable on `local.taranis.ai`.

## Technology stack

### Backend

* Python: Used for the core backend services including [REST API](../src/core/README.md).
* Celery: For managing asynchronous tasks and [worker processes](../src/worker/README.md).

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
