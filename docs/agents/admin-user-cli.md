# Admin User CLI

## When To Load

`taranis-cli`, password reset, role repair, or core-container user administration.

## Contracts

Run inside the core container against existing users:

- `set-password USERNAME` updates database authentication. Prefer the prompt or `--password-stdin`; never print passwords/hashes.
- `set-roles USERNAME ROLE...` replaces the complete role list, accepting exact role names or IDs.

The CLI starts Flask with `initial_setup=False`, validates references, and commits in an app context. It is for user repair, not creation.

The same entry point also provides `backfill-fuzzy-hashes`; its content, batching, and timestamp contracts belong to [Fuzzy Deduplication](fuzzy-deduplication.md).

## Entry Points and Coverage

`src/core/core/cli.py`; console entry in `src/core/pyproject.toml`; operator docs in `src/core/README.md` and `deploy/README.md`; tests in `src/core/tests/unit/test_cli.py`.
