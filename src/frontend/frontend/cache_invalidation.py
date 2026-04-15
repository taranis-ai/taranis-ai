"""Cache invalidation via Redis pub/sub

This module listens for cache invalidation signals from Core
and clears frontend cache when needed.
"""

import atexit
import threading
from time import sleep

from redis import Redis
from redis.exceptions import RedisError

from frontend.cache import invalidate_cache_keys
from frontend.log import logger


CACHE_INVALIDATION_CHANNEL = "taranis:cache:invalidate"
REDIS_SOCKET_TIMEOUT_SECONDS = 1
LISTENER_RETRY_DELAY_SECONDS = 1


class CacheInvalidationListener:
    """Listens for cache invalidation signals and clears frontend cache"""

    def __init__(self, redis_url: str, redis_password: str | None = None):
        self.redis_conn = Redis.from_url(
            redis_url,
            password=redis_password,
            decode_responses=True,
            socket_connect_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
            socket_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
        )
        self.pubsub = None
        self.listener_thread = None
        self._stop_event = threading.Event()

    def start(self):
        """Start listening for invalidation signals"""
        self.listener_thread = threading.Thread(target=self._listen_for_invalidation, daemon=True, name="CacheInvalidation")
        self.listener_thread.start()

    def stop(self):
        """Stop listening"""
        self._stop_event.set()
        if self.pubsub is not None:
            try:
                self.pubsub.unsubscribe(CACHE_INVALIDATION_CHANNEL)
                self.pubsub.close()
            except RedisError as exc:
                logger.warning(f"CacheInvalidationListener: failed to close pubsub cleanly: {exc}")
        if self.listener_thread:
            self.listener_thread.join(timeout=5)
        logger.info("CacheInvalidationListener: stopped")

    def _listen_for_invalidation(self):
        """Listen for pub/sub messages and invalidate cache"""
        logger.info("CacheInvalidationListener: listener thread started")

        while not self._stop_event.is_set():
            try:
                pubsub = self.redis_conn.pubsub()
                self.pubsub = pubsub
                pubsub.subscribe(CACHE_INVALIDATION_CHANNEL)
                logger.info(f"CacheInvalidationListener: subscribed to {CACHE_INVALIDATION_CHANNEL}")

                while not self._stop_event.is_set():
                    message = pubsub.get_message(timeout=REDIS_SOCKET_TIMEOUT_SECONDS)
                    if not message or message["type"] != "message":
                        continue

                    cache_key_suffix = str(message["data"])
                    logger.info(f"CacheInvalidationListener: received invalidation signal for: {cache_key_suffix}")
                    self._invalidate_cache(cache_key_suffix)
            except RedisError as exc:
                if self._stop_event.is_set():
                    break
                logger.warning(f"CacheInvalidationListener: Redis pub/sub unavailable, retrying: {exc}")
                sleep(LISTENER_RETRY_DELAY_SECONDS)
            finally:
                if self.pubsub is not None:
                    try:
                        self.pubsub.close()
                    except RedisError:
                        logger.debug("CacheInvalidationListener: pubsub already closed")
                self.pubsub = None

    def _invalidate_cache(self, suffix: str):
        """Invalidate cache entries matching the suffix"""
        try:
            invalidated = invalidate_cache_keys(suffix)
            if invalidated < 0:
                logger.info(f"CacheInvalidationListener: cleared entire cache for suffix: {suffix}")
                return
            logger.info(f"CacheInvalidationListener: invalidated {invalidated} cache entries for suffix: {suffix}")
        except Exception as exc:
            logger.exception(f"CacheInvalidationListener: failed to invalidate cache: {exc}")


# Global listener instance
_listener: CacheInvalidationListener | None = None


def start_cache_listener(redis_url: str, redis_password: str | None = None):
    """Start the cache invalidation listener"""
    global _listener
    if _listener is None:
        _listener = CacheInvalidationListener(redis_url, redis_password)
        _listener.start()


def stop_cache_listener():
    """Stop the cache invalidation listener"""
    global _listener
    if _listener:
        _listener.stop()
        _listener = None


atexit.register(stop_cache_listener)
