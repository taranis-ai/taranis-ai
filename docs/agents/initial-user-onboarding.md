# Initial User Onboarding

## When To Load

Initial database setup, pre-seeded users, onboarding tasks, `pre_seed_default_user`, or `SKIP_INITIAL_USER_ONBOARDING`.

## Expected Behavior

`SKIP_INITIAL_USER_ONBOARDING` defaults to `false` and presets the persistent global `onboarding_enabled` setting only while that setting is missing. A value of `true` presets onboarding to disabled; later changes in Admin Settings remain authoritative.

Changing the global setting updates every existing user's `profile.onboarding_enabled` value. An administrator can then override individual users in Admin Users, including enabling one user while the global setting remains disabled. New users inherit the current global value unless the create form explicitly overrides it.

Disabling onboarding suppresses pending tasks without changing completed, dismissed, or pending task state. An actual global value change replaces all existing per-user enabled flags; submitting the unchanged global value preserves individual overrides.

## Code Paths

- `src/core/core/config.py`
- `src/core/core/model/settings.py`
- `src/core/core/model/user.py`
- `src/models/models/user.py`
- `src/frontend/frontend/templates/settings/settings.html`
- `src/frontend/frontend/templates/user/user_form.html`
- `src/core/tests/test_settings.py`

## Data Flow

Core startup initializes the missing global setting from the environment flag and copies it to existing profiles. Admin Settings performs the same bulk copy only when the global value changes. The user profile response suppresses pending tasks when that user's enabled flag is false.

## Testing

Run from `src/core`:

- `uv run pytest tests/test_settings.py tests/unit/test_onboarding_settings.py`
- `uv run ruff check core/config.py core/model/settings.py core/model/user.py tests/test_settings.py tests/unit/test_onboarding_settings.py`

Run from `src/frontend`:

- `uv run pytest tests/test_settings.py tests/test_onboarding.py tests/unit/views/test_forms.py`
- `uv run pytest --e2e-ci`

## Pitfalls

- The environment flag must not overwrite an already-persisted global value.
- The global value is a bulk default, not a runtime gate; per-user overrides must remain effective until the global value actually changes.
- Never rewrite `onboarding_tasks` when enabling or disabling onboarding.
