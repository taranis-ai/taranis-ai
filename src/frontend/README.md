# Taranis AI Frontend

This service provides the Frontend for Taranis AI. In the first iteration it will only support Administration Part of the Admin Frontend with plans to Add "Assess", "Analyze" and "Publish" later on. It is based on a Flask web interface, utilizing **HTMX** for dynamic updates.

---

## Installation

Use the prebuilt container image from <https://github.com/orgs/taranis-ai/packages/container/package/taranis-frontend>

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

Assess sidebar filters can be saved per user using Save & manage searches beside the search box. The dialog lets users save the current search or apply and manage saved searches. Custom dates and Advanced filters expand when needed; active-filter chips share the top row with View and Create item and remove individual criteria. Saving with an existing saved filter name updates it, duplicate filter criteria under another name are rejected, and each saved filter can be updated from the current sidebar filters or deleted from the dashboard cards. One saved filter can be marked as the default; loading `/assess` without query parameters redirects to that saved filter, while `?reset=true` shows the unfiltered list.

The Time period dropdown offers Any time, Today (shift), This week, This month, Last 24 hours, Last 7 days, and Last 30 days. Calendar periods start at midnight UTC (Monday for the week); rolling periods count back from the current time. This corrects the previous midnight-based cutoff for `24h` and `last<N>`, including saved searches using those values. Existing `day` and other `last<N>` URLs remain selectable. Custom dates further constrain a preset. Selecting Any time clears the preset and custom dates while retaining other filters; custom-only filters display Custom dates until cleared. The information tooltip explains UTC calendar boundaries, which keep shared filter URLs independent of the viewer’s time zone.

Sort labels distinguish Story date, Updated, and Relevance; the information tooltip explains each. Story date uses `created`, normally the earliest news-item publication date, rather than collection time. Updated uses the last story update. Relevance sorts by story score, with search rank taking precedence for full-text searches.

Story headlines open the story; checkboxes select stories for bulk actions. Read, Important, Bookmark, and Add to report are available directly in the footer after the summary and tags, grouped separately from Show details and More. Details and More load on demand. The View menu changes compact mode and search highlighting without navigating away or clearing the selection. Bulk changes are atomic: every selected story updates, or the transaction rolls back all updates and revisions.

Story cards always show and highlight tags matching an active tag-name or tag-type filter, including in compact view. The `+N` button expands just the tags; Show fewer tags collapses them again. Opening story details also shows all tags.

Expanded stories show each news item's source name, Published and Collected dates, author, and TLP label when available, alongside its original link. Source names are resolved per item from the user-visible catalog, independently of the five-source icon limit on the story; items outside the catalog retain their own source description. Manually added items are identified by their source ID even with a custom description. The same metadata row appears on full news-item cards; missing values are omitted. Language is shown on full detail cards, not in the expanded overview.

Story details and editing include Back to Assess, preserving the search filters and page you opened the story from, including after saving or switching editor layouts. Marking an infinite-scroll story read or important preserves that card's loaded page for its Open/Edit return links. Assess also remembers the last search in this browser per user and offers to restore it when opening Assess without filters. Dismiss clears that remembered search; explicit filters, saved defaults, and Reset filters take precedence. Return links work without JavaScript or browser storage.

Restoring an infinite-scroll search partway through the results shows its starting position and explains that earlier results are not loaded. Start from beginning keeps the same filters and lets you browse all matching stories. The counter reports stories loaded, and the footer shows the loaded result range and End of results when there are no later matches.

Colon-containing terms that are not supported qualifiers, such as URLs or CVE-style identifiers, are preserved as plain search text.

### Story Bookmarks

Bookmarks are private story bookmarks organized into named collections. Assess shows the first six collections in the user's saved order and links to the full `/bookmarks` page, where users can drag collection cards to reorder them. Users can select stories in Assess, bookmark them into an existing or new collection with `Bookmark`, and later manage those collections from `/bookmarks`. A single story card's `Bookmark` action immediately adds the story to the first saved collection; if no collection exists yet, a default `Bookmarks` collection is created. Bookmarking a story does not hide it from Assess, and deleting a bookmark collection only removes the collection membership, not the stories.

### Analyst Chat

When `CHAT_ENABLED=true`, users with `ASSESS_ACCESS` see a persistent `/chat` workspace. Chat operations intentionally bypass the frontend model cache. Search answers contain escaped plain text, a match count, and one canonical `/assess` filter link; provider-generated HTML, Markdown, and links are not rendered.

The frontend waits up to `CHAT_REQUEST_TIMEOUT` seconds (default 600 in `src/frontend/frontend/config.py`) for the authoritative synchronous core workflow. With realtime enabled, the existing Centrifugo connection also shows the submitted message immediately, displays Planning/Searching/Writing stages, and replaces the assistant bubble with cumulative plain-text snapshots. Missing or failed realtime delivery simply leaves the progress indicator visible until the completed HTMX response arrives. Provider configuration and credentials belong to core deployment settings, not the frontend.

### Notifications

Notifications may set `persistent: true` to remain visible until the user dismisses them. Administrators with `ADMIN_OPERATIONS` can use the dedicated Notifications page in the admin sidebar to send a persistent message of up to 500 characters to all connected users; the exact text is delivered through the existing Centrifugo realtime connection and recorded in each tab's Notification Center. The page also shows a live snapshot of connected clients and unique users, including usernames resolved by core.

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

Internationalization is currently experimental. At the moment, translated coverage includes login, user settings, and bookmarks.

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

- [DaisyUI](https://daisyui.com/docs/intro/)
- [tailwindCSS](https://tailwindcss.com/docs)
- [Jinja](https://jinja.palletsprojects.com/en/stable/templates/)
- [HTMX 4](https://four.htmx.org/docs/)

### 1. Download and Setup Tailwind CSS

We use Tailwind CSS for styling the frontend. First, download the Tailwind CSS CLI tool:

```bash
./install_and_run_tailwind.sh
```

This will first download the **Tailwind CSS CLI** from <https://github.com/tailwindlabs/tailwindcss> and
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
