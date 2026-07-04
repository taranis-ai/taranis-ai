from collections.abc import Callable
from typing import Any


class FakeRedis:
    def ping(self):
        return True


def fake_queue_factory(queue_calls: list[dict[str, object]]) -> Callable[..., object]:
    class FakeQueue:
        def __init__(self, name: str, connection: object | None = None, default_timeout: int | None = None, **kwargs: Any):
            queue_calls.append(
                {
                    "name": name,
                    "connection": connection,
                    "default_timeout": default_timeout,
                }
            )

    return FakeQueue
