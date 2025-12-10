from flask import Flask
from frontend import router
from frontend.config import Config
from frontend import auth
from frontend import cache
from frontend import setup
from frontend import cache_invalidation


def create_app():
    app = Flask(__name__, static_url_path=f"{Config.APPLICATION_ROOT}/static")
    app.config.from_object("frontend.config.Config")

    with app.app_context():
        init(app)

    return app


def init(app: Flask):
    cache.init(app)
    auth.init(app)
    setup.init(app)
    router.init(app)
    
    # Start cache invalidation listener (pub/sub)
    try:
        cache_invalidation.start_cache_listener(
            app.config["REDIS_URL"],
            app.config.get("REDIS_PASSWORD")
        )
    except Exception as e:
        # Don't fail startup if cache invalidation listener can't start
        from frontend.log import logger
        logger.warning(f"Failed to start cache invalidation listener: {e}")
