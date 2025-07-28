# Taranis AI Frontend

This service provides the Frontend for Taranis AI. In the first iteration it will only support Administration Part of the Admin Frontend with plans to Add "Assess", "Analyze" and "Publish" later on. It is based on a Flask web interface, utilizing **HTMX** for dynamic updates.

---

## Installation

Use the prebuilt container image from https://github.com/orgs/taranis-ai/packages/container/package/taranis-frontend


Or create a local setup for which it's recommended to use a uv to setup an virtual environment.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
```

Source venv and install dependencies

```bash
source .venv/bin/activate
uv sync --frozen
```

## Usage

```bash
granian app
```

## Development Setup

### 0. Read the documentation

* [DaisyUI](https://daisyui.com/docs/intro/)
* [tailwindCSS](https://tailwindcss.com/docs)
* [Jinja](https://jinja.palletsprojects.com/en/stable/templates/)
* [HTMX](https://htmx.org/docs/)

### 1. Download and Setup Tailwind CSS

We use Tailwind CSS for styling the frontend. First, download the Tailwind CSS CLI tool:

```bash
./install_and_run_tailwind.sh
```

This will first download the **Tailwind CSS CLI** from https://github.com/tailwindlabs/tailwindcss and
execute it in watch mode to automatically build the CSS files as you modify the styles:

### 2. Start Flask

Run the Flask development server:

```bash
./install_and_run_dev.sh
```

This will start the Flask server and run the frontend service at `http://localhost:5000`.


### 3. Test

To run the unit tests just call:

```bash
pytest
```

There are [e2e tests](./tests/playwright/README.md) using playwright
