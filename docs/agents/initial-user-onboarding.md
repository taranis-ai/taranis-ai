# Initial User Onboarding

## When To Load

Initial database setup, pre-seeded users, onboarding tasks, `pre_seed_default_user`, or `SKIP_INITIAL_USER_ONBOARDING`.

## Expected Behavior

`SKIP_INITIAL_USER_ONBOARDING` defaults to `false`. When it is `true` during the first core startup against an empty database, all known onboarding tasks are stored as completed in the profiles of the pre-seeded `admin` and `user` accounts.

The flag does not change existing users, users created later, or the pending-task calculation used by the API. Users can still reset onboarding from their profile settings.

## Code Paths

- `src/core/core/config.py`
- `src/core/core/managers/db_seed_manager.py`
- `src/core/core/model/user.py`
- `src/models/models/user.py`
- `src/core/tests/test_settings.py`

## Data Flow

Core startup reads the environment flag into `Config`. Empty-database pre-seeding creates the initial accounts with completed onboarding task statuses. The normal user profile response then reports no pending onboarding tasks.

## Testing

Run from `src/core`:

- `uv run pytest tests/test_settings.py`
- `uv run ruff check core/config.py core/managers/db_seed_manager.py tests/test_settings.py`

## Pitfalls

- The flag is intentionally one-time: setting it after users already exist must not rewrite their profiles.
- Keep the completed task IDs aligned with the onboarding constants in `models.user`.
- Do not globally suppress pending onboarding tasks, because that would also affect later-created users.
