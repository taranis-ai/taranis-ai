# Global Settings

Load for: Persistent core settings, `Settings.get_settings()`, defaults, or settings cache behavior.

## Contracts

- `Settings.get_settings()` caches a detached snapshot per SQLAlchemy session/transaction and returns deep copies, including nested custom values.
- Flush, commit, rollback, and savepoint completion clear it. Pending writes bypass caching to preserve autoflush; missing rows are never cached.
- No cross-request/process cache, Redis, or TTL: unchanged transactions reuse the first read; external changes appear in subsequent transactions subject to isolation.
- Initialization and onboarding follow [Initial User Onboarding](initial-user-onboarding.md).

## Code and Tests

`src/core/core/model/settings.py`; `src/core/tests/test_settings.py` covers query reuse, mutation isolation, pending updates, commit, and savepoint rollback. Existing initialization and onboarding tests cover writes through `initialize()` and `update()`.
