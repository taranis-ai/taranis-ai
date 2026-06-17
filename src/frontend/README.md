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

### Omnisearch

The navbar search sends users to `GET /search?q=...`. Unqualified searches render grouped results across Stories, Reports, and Products with links to matching objects and to each filtered list view.

Scope prefixes jump straight to the existing list views: `story: <search>` opens `/assess?search=<search>`, `report: <search>` opens `/analyze?search=<search>`, and `product: <search>` opens `/publish?search=<search>`. The aliases `stories:`, `assess:`, `reports:`, `analyze:`, `products:`, and `publish:` are also accepted. `report:true` and `report:false` are reserved for the Assess `in_report` filter; use `report: <search>` for report search.

Assess keyword filters are implicit story mode. `vpn tag:apt read:false sort:relevance` opens `/assess` with the same query parameters as the Assess sidebar. Supported Assess qualifiers are `source:`, `group:`, `tag:`/`tags:`, `read:`, `important:`, `relevant:`, `in-report:`/`report:`, `cybersecurity:`/`cyber:`, `changed-by:`, `range:`, `from:`, `to:`, and `sort:`. `range:` accepts `shift`, `24h`, `week`, `day`, `month`, and `last<N>` values such as `last7`.

Colon-containing terms that are not supported qualifiers, such as URLs or CVE-style identifiers, are preserved as plain search text.

### Cache configuration

Frontend caching now uses Redis directly and falls back to a no-op cache when disabled or when Redis is unavailable.

- `src/models/models/cache_contract.py` defines the shared cache defaults and key/pattern helpers used by both core and frontend
- `CACHE_ENABLED=true|false` toggles frontend caching
- `CACHE_REDIS_URL` optionally overrides the Redis URL used for cache storage
- `CACHE_REDIS_PASSWORD` optionally overrides the Redis password used for cache storage
- when the cache-specific settings are unset, frontend falls back to `REDIS_URL` and `REDIS_PASSWORD`
- unit tests disable caching by default unless `CACHE_ENABLED=true` is explicitly set in the test app config

### Internationalization

The frontend uses Flask-Babel for server-rendered translations. English is the default locale and German is the first translated catalog.

Internationalization is currently experimental. At the moment, translated coverage is limited to login and user settings.

Extract strings after changing translated templates or Python strings:

```bash
uv run pybabel extract -F babel.cfg -o frontend/translations/messages.pot frontend
```

Initialize a new German catalog once:

```bash
uv run pybabel init -i frontend/translations/messages.pot -d frontend/translations -l de
```

Update existing catalogs after extraction:

```bash
uv run pybabel update -i frontend/translations/messages.pot -d frontend/translations
```

Compile catalogs before runtime or packaging:

```bash
uv run pybabel compile -d frontend/translations
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

There are [e2e tests](./tests/playwright/README.md) using Playwright, including the browser suite and the RQ/Redis integration e2e suite.
