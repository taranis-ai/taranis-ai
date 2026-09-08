# Initial User Onboarding

## When To Load

Seeded users, onboarding tasks/settings, `pre_seed_default_user`, or `SKIP_INITIAL_USER_ONBOARDING`.

## Contracts

- `SKIP_INITIAL_USER_ONBOARDING=false` by default. It initializes only a missing persistent global `onboarding_enabled` setting; `true` presets that setting to disabled. Later Admin Settings values are authoritative.
- An actual global value change copies the flag to every existing user's profile. Saving the unchanged value preserves per-user overrides. New users inherit the global value unless explicitly overridden at creation.
- The global value is a bulk default, not a runtime gate: individual users can be enabled while it is disabled. Disabling hides pending tasks without rewriting task completion/dismissal state.
- Administrator tours require `ADMIN_OPERATIONS`; there is no catch-all `ALL` permission.
- Fresh databases seed `admin`/`user` as Default Admin/Default User in one Default Organization.

## Entry Points and Coverage

`src/core/core/managers/db_seed_manager.py`, `src/core/core/model/settings.py`, `src/core/core/model/user.py`, `src/models/models/user.py`; frontend settings/user forms.

Tests: `src/core/tests/test_settings.py`, `src/core/tests/unit/test_onboarding_settings.py`, `src/frontend/tests/test_onboarding.py`, `src/frontend/tests/unit/views/test_forms.py`, and admin user management in `src/frontend/tests/playwright/test_e2e_admin.py`.
