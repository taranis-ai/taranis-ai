# Admin User Import/Export

## When To Load
Admin users page, user export/import, `/api/config/users-import`, `/api/config/users-export`, external users, passwordless users, duplicate usernames, `user_import.html`.

## Expected Behavior
User export writes `version: 1` JSON with `data` records containing `name` and `username`; passwords are not exported.

User import assigns the selected organization and roles in the frontend before sending records to core. Imported records without a `password` stay passwordless in the database. Duplicate usernames are skipped and reported to the caller instead of failing the whole import.

Malformed JSON, undecodable bytes, or files that do not match the exported `version`/`data` shape should render a normal admin notification and must not leak a Flask traceback into the page.

## Code Paths
Core import/export lives in `src/core/core/model/user.py` and `src/core/core/api/config.py`.

Frontend import/export lives in `src/frontend/frontend/views/admin_views/user_views.py` and `src/frontend/frontend/templates/user/user_import.html`.

## Data Flow
The admin import form uploads an exported JSON file, selected organization, and selected roles. The frontend expands each exported user record with `organization` and `roles`, then posts the list to `/api/config/users-import`.

Core creates only missing users, returns `users`/`count` for created users and `skipped_users`/`skipped_count` for duplicates or invalid entries, and always includes a user-facing `message` for successful or no-op imports. Skipped entries include `username` and `reason`.

The frontend renders successful imports with no skipped users as success notifications. Any import response with `skipped_count > 0`, including all-skipped no-op imports, should show a warning notification.

## Testing
Core coverage belongs in `src/core/tests/application/admin_console/configuration/test_config_api.py`.

Frontend route/template coverage belongs in `src/frontend/tests/unit/views/test_forms.py`.

Run targeted validation with `DEBUG=true` from each component directory.

## Pitfalls
Do not generate hidden passwords for exported/imported external users. Database username/password login requires a stored password hash, but external authentication can use passwordless user rows.

Do not treat duplicate-only imports as `400`; that breaks HTMX import handling and hides the skipped-user details from the UI.

Use `response.ok` in frontend import handling. A `requests.Response` with a 4xx status is falsy, so `if not response` incorrectly conflates core errors with no response.

Catch frontend JSON parsing and shape errors before posting to core; otherwise HTMX swaps the Flask debug traceback into the import form.

Keep core defensive too. A malformed item in a list posted directly to `/api/config/users-import` should be skipped with a reason while valid items in the same batch are still imported.

Stage all valid imported users first and commit them as one batch. Do not call per-user `add()` from import code; a commit failure must roll back every staged user so there are no partial inserts.
