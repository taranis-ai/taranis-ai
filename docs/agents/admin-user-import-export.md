# Admin User Import/Export

## When To Load

Admin user JSON import/export, `/api/config/users-import`, `/api/config/users-export`, duplicates, or passwordless external users.

## Contracts

- Export is `version: 1` JSON with `data` records containing `name` and `username`, never passwords. Frontend import adds the selected organization and roles before posting records to core.
- Missing passwords stay absent; do not generate hidden credentials. External authentication supports passwordless rows, while database login requires a stored hash.
- Skip duplicate usernames and malformed individual records while importing valid records. Return `users`/`count`, `skipped_users`/`skipped_count`, and a message with both counts; skipped entries include `username` and `reason`.
- Any skipped entries produce a warning, including duplicate-only no-ops; these are not 400 responses. Stage all valid users and commit once so commit failure cannot leave partial inserts.
- Frontend rejects malformed JSON, undecodable bytes, and invalid export shape before calling core, using normal notifications. Distinguish an absent response from a failed one with `response.ok`: error responses are falsy in `requests`.

## Entry Points and Coverage

Core: `src/core/core/model/user.py`, `src/core/core/api/config.py`. Frontend: `src/frontend/frontend/views/admin_views/user_views.py`, `src/frontend/frontend/templates/user/user_import.html`.

Tests: `src/core/tests/application/admin_console/configuration/test_config_api.py`, `src/frontend/tests/unit/views/test_forms.py`.
