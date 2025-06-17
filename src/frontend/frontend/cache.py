from flask_caching import Cache
from frontend.config import Config
from models.admin import User
from frontend.log import logger

cache = Cache()


def add_user_to_cache(user: dict) -> User | None:
    try:
        user_object = User(**user)
        cache.set(key=f"user_cache_{user['username']}", value=user_object, timeout=Config.CACHE_DEFAULT_TIMEOUT)
        return user_object
    except Exception:
        logger.exception("Failed to add user to cache")
        return None


def get_user_from_cache(username: str) -> User | None:
    return cache.get(f"user_cache_{username}")


def remove_user_from_cache(username: str):
    cache.delete(f"user_cache_{username}")


def list_cache_keys():
    return cache.cache._cache.keys()


def get_cached_users() -> list[User]:
    prefix = "user_cache_"
    users = []
    for key in cache.cache._cache:
        username = key.removeprefix(prefix)
        if username == key:
            continue
        if user := get_user_from_cache(username):
            users.append(user)
    return users


def init(app):
    cache.init_app(app)
