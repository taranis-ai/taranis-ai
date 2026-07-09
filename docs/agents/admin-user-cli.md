# Admin User CLI

## When To Load

User password reset, user role repair, `taranis-cli`, `set-password`, `set-roles`, Docker or Kubernetes exec into the core container.

## Expected Behavior

Operators can run `taranis-cli` inside the core container to update existing users without going through the frontend.

`set-password USERNAME` updates the database-auth password for an existing user. It must not print the password or hash.

`set-roles USERNAME ROLE...` replaces the user's complete role list. Role arguments can be exact role names or role IDs.

## Code Paths

- CLI: `src/core/core/cli.py`
- Console script: `src/core/pyproject.toml`
- User model: `src/core/core/model/user.py`
- Role model: `src/core/core/model/role.py`
- Operator docs: `src/core/README.md`, `deploy/README.md`

## Data Flow

The CLI creates a core Flask app with `initial_setup=False`, opens an app context, loads the target user, validates role references when needed, and commits through SQLAlchemy.

## Testing

Run from `src/core`:

```bash
uv run pytest tests/unit/test_cli.py
uv run ruff format core/cli.py tests/unit/test_cli.py
uv run ruff check core/cli.py tests/unit/test_cli.py
```

Run from the repository root after Python edits:

```bash
./dev/check_touched_pyright.sh
```

## Pitfalls

Do not create users from this CLI unless explicitly requested; it is for existing-user repair.

Do not log or echo passwords. Prefer the prompt or `--password-stdin` in docs.

Keep `set-roles` replacement semantics explicit; appending roles can hide broken assignments.
