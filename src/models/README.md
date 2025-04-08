# Taranis AI Models

This folder provides models for validation of data sent between Taranis AI services and offered to third party clients.

## Installation

It's recommended to use a uv to set up a virtual environment.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
```

Source venv and install dependencies

```bash
source .venv/bin/activate
uv pip install -Ue .[dev]
```

