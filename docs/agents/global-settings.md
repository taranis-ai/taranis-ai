# Global Settings

## When To Load

Persistent core settings, `Settings.get_settings()`, defaults, or settings cache behavior.

## Contracts

- `Settings.get_settings()` caches a detached dictionary in the current SQLAlchemy session for the current transaction. Repeated reads without pending writes issue one settings query; every caller receives a deep copy, including nested custom values.
- Flush and transaction end (including commit, rollback, and savepoint completion) clear the snapshot. Pending writes bypass it to preserve query autoflush behavior. Missing rows are not cached, so initialization can create the singleton normally.
- The cache is not shared across requests, sessions, or core processes. It avoids repeated queries within a transaction; it does not eliminate the first query per transaction. Changes from other processes become visible on a subsequent transaction, subject to database isolation. No Redis or TTL configuration is involved.
- Initialization and global onboarding propagation retain the contracts in [Initial User Onboarding](initial-user-onboarding.md).

## Entry Points and Coverage

`src/core/core/model/settings.py`; `src/core/tests/test_settings.py` covers query reuse, mutation isolation, pending updates, commit, and savepoint rollback. Existing initialization and onboarding tests cover writes through `initialize()` and `update()`.
