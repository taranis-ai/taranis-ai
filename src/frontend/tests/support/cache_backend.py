from fnmatch import fnmatch
from typing import Any


class InMemoryRedisClient:
    def __init__(self, initial: dict[str, Any] | None = None):
        self.store: dict[str, Any] = dict(initial or {})

    def ping(self):
        return True

    def get(self, key: str):
        return self.store.get(key)

    def set(self, name: str, value: Any, ex: int | None = None, **_kwargs: Any) -> bool:
        self.store[name] = value
        return True

    def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if self.store.pop(key, None) is not None:
                deleted += 1
        return deleted

    def clear(self) -> int:
        deleted = len(self.store)
        self.store.clear()
        return deleted

    def scan_iter(self, match: str, count: int = 1000):
        yield from sorted(key for key in self.store if fnmatch(key, match))
