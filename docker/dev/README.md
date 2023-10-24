# Taranis AI Development setup


## Easy Mode


Copy env.dev to worker and core

```bash
cp docker/dev/env.dev src/core/.env
cp docker/dev/env.dev src/worker/.env
```


```bash
./start_dev.sh
```

## Hard Mode


Starting from the git root:

```bash
cd $(git rev-parse --show-toplevel)
```

Copy env.dev to worker and core

```bash
cp docker/dev/env.dev src/core/.env
cp docker/dev/env.dev src/worker/.env
```

Start support services via the dev compose file

```bash
docker compose -f docker/dev/compose.yml up -d
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
python3 -m venv venv

# Activate venv
source venv/bin/activate

# Install requirements
pip install -e .[dev]

# Run core
flask run
```


In Worker Tab:

```bash
# If venv isn't setup already
python3 -m venv venv

# Activate venv
source venv/bin/activate

# Install requirements
pip install -e .[dev]

# Run worker
celery -A worker worker
```

In GUI Tab:

```bash
# If node modules isn't setup already
npm install

# Run GUI
npm run dev
```
