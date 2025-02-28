from flask_caching import Cache

class FrontendCache:
    def __init__(self):
        self.cache = Cache()

    # TODO: explain this method
    def init_app(self, app):
        self.cache.init_app(app)

    def get(self, key):
        return self.cache.get(key)
    
    def set(self, key, value, timeout=None):
        return self.cache.set(key, value, timeout)

cache = FrontendCache()