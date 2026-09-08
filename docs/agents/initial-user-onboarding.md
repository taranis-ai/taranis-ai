# Initial User Onboarding

## When To Load

Seeded users, onboarding tasks/settings, `pre_seed_default_user`, or `PRE_SEED_SETTINGS`.

## Contracts

- Onboarding defaults to enabled. Set `PRE_SEED_SETTINGS='{"onboarding_enabled":false}'` to disable it during settings initialization; later Admin Settings values remain authoritative.
- An actual global value change copies the flag to every existing user's profile. Saving the unchanged value preserves per-user overrides. New users inherit the global value unless explicitly overridden at creation.
- The global value is a bulk default, not a runtime gate: individual users can be enabled while it is disabled. Disabling hides pending tasks without rewriting task completion/dismissal state.
- Administrator tours require `ADMIN_OPERATIONS`; there is no catch-all `ALL` permission.
- Fresh databases seed `admin`/`user` as Default Admin/Default User in one Default Organization.
- `PRE_SEED_SETTINGS` accepts a flat JSON object for any global settings. `Settings.initialize()` applies it only when no singleton settings row exists, filling omitted keys with normal defaults and copying onboarding to existing profiles. Subsequent startup preserves persisted settings. An existing row missing `onboarding_enabled` receives the default `true`. JSON parsing uses Pydantic Settings and initialization reuses existing timezone, integer, and boolean validators. Deployment examples are in `docker/README.md`.

## Entry Points and Coverage

`src/core/core/managers/db_seed_manager.py`, `src/core/core/model/settings.py`, `src/core/core/model/user.py`, `src/models/models/user.py`; frontend settings/user forms.

Tests: `src/core/tests/test_settings.py`, `src/core/tests/unit/test_onboarding_settings.py`, `src/frontend/tests/test_onboarding.py`, `src/frontend/tests/unit/views/test_forms.py`, and admin user management in `src/frontend/tests/playwright/test_e2e_admin.py`.
