# Taranis AI Frontend

This service provides the Frontend for Taranis AI. In the first iteration it will only support Administration Part of the Admin Frontend with plans to Add "Assess", "Analyze" and "Publish" later on. It is based on a Flask web interface, utilizing **HTMX** for dynamic updates.

---

## Installation

It's recommended to use a uv to setup an virtual environment.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
```

Source venv and install dependencies

```bash
source .venv/bin/activate
uv pip install -Ue .[dev]
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
curl -sLo tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64
chmod +x tailwindcss
```

### 2. Start Tailwind CSS in Watch Mode

Run **Tailwind CSS** in watch mode to automatically build the CSS files as you modify the styles:

```bash
./tailwindcss -i frontend/static/css/input.css -o frontend/static/css/tailwind.css --watch
```

This will generate the `tailwind.css` file based on the input CSS and keep it updated as you develop.

### 3. Start Flask

Run the Flask development server:

```bash
flask run
```

This will start the Flask server and run the frontend service at `http://localhost:5000`.
