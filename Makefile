# Convenience entry points for the named OrcaRouter provider.
#
# The project toolchain is uv. When uv is installed with
# `python3 -m pip install --user uv`, its binary lives under ~/.local/bin;
# override with `make UV=/path/to/uv <target>` when it is elsewhere.

UV ?= $(HOME)/.local/bin/uv
CORE := src/core
FRONTEND := src/frontend

# The "dev" extras install lint, type-check, browser-automation and documentation
# toolchains that these checks do not exercise. Skipping them keeps every target
# inside a 10-minute budget on a cold package cache. Drop the flags to prepare a
# complete development environment.
SKIP_TOOLS := --no-install-package pyrefly --no-install-package pyright \
              --no-install-package ruff --no-install-package schemathesis
SKIP_BROWSER := --no-install-package playwright --no-install-package pytest-playwright

export UV_HTTP_TIMEOUT := 180

.PHONY: orcarouter-sync orcarouter-browser orcarouter-frontend-env
.PHONY: orcarouter-catalog orcarouter-provider orcarouter-regression orcarouter-live
.PHONY: orcarouter-frontend orcarouter-gui

# Resolve the environments and make the PostgreSQL driver importable without a
# system libpq, matching the repository's psycopg version.
orcarouter-sync:
	$(UV) sync --frozen --all-extras --directory $(CORE) $(SKIP_TOOLS) $(SKIP_BROWSER)
	$(UV) pip install --python $(CORE)/.venv psycopg-binary==3.3.6

# The admin-UI check drives headless Chromium through Playwright, the only use of
# the browser half of the Core dev extra.
orcarouter-browser:
	$(UV) sync --frozen --all-extras --directory $(CORE) $(SKIP_TOOLS)
	$(UV) pip install --python $(CORE)/.venv psycopg-binary==3.3.6

orcarouter-frontend-env:
	$(UV) sync --frozen --all-extras --directory $(FRONTEND) $(SKIP_TOOLS) $(SKIP_BROWSER) --no-install-package djlint

orcarouter-catalog: orcarouter-sync
	$(UV) run --no-sync --frozen --directory $(CORE) pytest tests/unit/test_llm_catalog.py -q

orcarouter-provider: orcarouter-sync
	$(UV) run --no-sync --frozen --directory $(CORE) pytest tests/application/admin_console/operations/test_admin_api.py::TestAdminApi::test_orcarouter_provider_and_model_catalog -q

orcarouter-regression: orcarouter-sync
	$(UV) run --no-sync --frozen --directory $(CORE) pytest tests/test_settings.py -q

orcarouter-live: orcarouter-sync
	$(UV) run --no-sync --frozen --directory $(CORE) pytest tests/unit/test_orcarouter_live.py -q

orcarouter-frontend: orcarouter-frontend-env
	$(UV) run --no-sync --frozen --directory $(FRONTEND) pytest tests/test_settings.py -q

orcarouter-gui: orcarouter-browser orcarouter-frontend-env
	@test -s $(FRONTEND)/frontend/static/vendor/vendor.bundle.js
	$(UV) run --no-sync --frozen --directory $(CORE) pytest tests/unit/test_orcarouter_gui_evidence.py -q
