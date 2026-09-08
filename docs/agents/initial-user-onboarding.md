# Initial User Onboarding

## When To Load

Initial database setup, pre-seeded users, onboarding tasks, `pre_seed_default_user`, or `PRE_SEED_SETTINGS`.

## Expected Behavior

Onboarding defaults to enabled. Set `PRE_SEED_SETTINGS='{"onboarding_enabled":false}'` to disable it during settings initialization; later changes in Admin Settings remain authoritative.

`PRE_SEED_SETTINGS` accepts a flat JSON object for any global settings. `Settings.initialize()` applies it only when no singleton settings row exists, filling omitted keys with normal defaults. The initialized `onboarding_enabled` value is copied to existing users. Subsequent startup preserves persisted settings and does not merge seed values. JSON parsing is handled by Pydantic Settings; initialization reuses existing timezone, integer, and boolean validators. Environment parsing and persistence/restart coverage live in `src/core/tests/test_settings.py`; deployment examples are in `docker/README.md`.

Changing the global setting updates every existing user's `profile.onboarding_enabled` value. An administrator can then override individual users in Admin Users, including enabling one user while the global setting remains disabled. New users inherit the current global value unless the create form explicitly overrides it.

Disabling onboarding suppresses pending tasks without changing completed, dismissed, or pending task state. An actual global value change replaces all existing per-user enabled flags; submitting the unchanged global value preserves individual overrides.

Pending administrator tours require the real `ADMIN_OPERATIONS` permission. Taranis has no catch-all `ALL` permission, so backend and frontend onboarding checks must not treat that string specially.

Fresh databases seed the `admin` and `user` accounts as `Default Admin` and `Default User`. Both accounts belong to the single `Default Organization`.

## Code Paths

- `src/core/core/config.py`
- `src/core/core/managers/db_seed_manager.py`
- `src/core/core/model/asset.py`
- `src/core/core/model/settings.py`
- `src/core/core/model/user.py`
- `src/models/models/user.py`
- `src/frontend/frontend/templates/settings/settings.html`
- `src/frontend/frontend/templates/user/user_form.html`
- `src/frontend/tests/playwright/testdata/test_users_list.json`
- `src/core/tests/test_settings.py`

## Data Flow

Core startup seeds a new settings row from `PRE_SEED_SETTINGS` and copies onboarding to existing profiles. An existing row missing `onboarding_enabled` receives the default `true`. Admin Settings performs the same bulk copy only when the global value changes. The user profile response suppresses pending tasks when that user's enabled flag is false.

## Testing

Run from `src/core`:

- `uv run pytest tests/test_settings.py tests/unit/test_onboarding_settings.py`
- `uv run ruff check core/config.py core/model/settings.py core/model/user.py tests/test_settings.py tests/unit/test_onboarding_settings.py`

Run from `src/frontend`:

- `uv run pytest tests/test_settings.py tests/test_onboarding.py tests/unit/views/test_forms.py`
- `uv run pytest tests/playwright/test_e2e_admin.py::TestEndToEndAdmin::test_admin_user_management --e2e-ci`
- `uv run pytest --e2e-ci`

## Pitfalls

- The JSON seed must not overwrite an existing settings row.
- The global value is a bulk default, not a runtime gate; per-user overrides must remain effective until the global value actually changes.
- Never rewrite `onboarding_tasks` when enabling or disabling onboarding.
