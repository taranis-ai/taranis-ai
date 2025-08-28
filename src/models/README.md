# Taranis AI Pydantic Models

This folder provides pydantic models for validation of data sent between Taranis AI services and offered to third party clients.

## Installation

It's recommended to use a uv to set up a virtual environment.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

If updating something and wanting to test it in `frontend` or `core` you can use `install_and_run_dev.sh` or something similar to the commands below:

```bash
uv sync --all-extras --frozen --python 3.13
uv pip install -e ../models

export UV_NO_SYNC=true
uv run pytest tests
```
