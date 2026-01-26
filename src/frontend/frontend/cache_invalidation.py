"""Cache invalidation via Redis pub/sub

This module listens for cache invalidation signals from Core
and clears frontend cache when needed.
"""

import threading

from redis import Redis

from frontend.cache import cache
from frontend.log import logger


CACHE_INVALIDATION_CHANNEL = "taranis:cache:invalidate"


class CacheInvalidationListener:
    """Listens for cache invalidation signals and clears frontend cache"""

    def __init__(self, redis_url: str, redis_password: str | None = None):
        self.redis_conn = Redis.from_url(redis_url, password=redis_password, decode_responses=True)
        self.pubsub = self.redis_conn.pubsub()
        self.listener_thread = None
        self._stop_event = threading.Event()

    def start(self):
        """Start listening for invalidation signals"""
        self.pubsub.subscribe(CACHE_INVALIDATION_CHANNEL)
        logger.info(f"CacheInvalidationListener: subscribed to {CACHE_INVALIDATION_CHANNEL}")

        self.listener_thread = threading.Thread(target=self._listen_for_invalidation, daemon=True, name="CacheInvalidation")
        self.listener_thread.start()

    def stop(self):
        """Stop listening"""
        self._stop_event.set()
        self.pubsub.unsubscribe(CACHE_INVALIDATION_CHANNEL)
        self.pubsub.close()
        if self.listener_thread:
            self.listener_thread.join(timeout=5)
        logger.info("CacheInvalidationListener: stopped")

    def _listen_for_invalidation(self):
        """Listen for pub/sub messages and invalidate cache"""
        logger.info("CacheInvalidationListener: listener thread started")

        for message in self.pubsub.listen():
            if self._stop_event.is_set():
                break

            if message["type"] == "message":
                cache_key_suffix = message["data"]
                logger.info(f"CacheInvalidationListener: received invalidation signal for: {cache_key_suffix}")
                self._invalidate_cache(cache_key_suffix)

    def _invalidate_cache(self, suffix: str):
        """Invalidate cache entries matching the suffix"""
        try:
            # Get all cache keys
            keys = list(cache.cache._cache.keys())
            invalidated = 0

            for key in keys:
                # Match keys ending with the suffix (e.g., "_config_schedule")
                if suffix and key.endswith(f"_{suffix}") or key.endswith(f"_{suffix.replace('/', '_')}"):
                    cache.delete(key)
                    invalidated += 1
                    logger.debug(f"Invalidated cache key: {key}")

            logger.info(f"CacheInvalidationListener: invalidated {invalidated} cache entries for suffix: {suffix}")

        except Exception as e:
            logger.exception(f"CacheInvalidationListener: failed to invalidate cache: {e}")


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
