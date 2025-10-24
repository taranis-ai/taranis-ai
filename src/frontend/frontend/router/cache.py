from flask import Flask, Blueprint, Response
from flask.views import MethodView

from frontend.data_persistence import DataPersistenceLayer
from frontend.auth import api_key_required


class InvalidateCache(MethodView):
    @api_key_required
    def get(self, suffix: str | None = None):
        if not suffix:
            DataPersistenceLayer().invalidate_cache(None)
        DataPersistenceLayer().invalidate_cache(suffix)
        return "Cache invalidated"

    @api_key_required
    def post(self, suffix: str | None = None):
        if not suffix:
            DataPersistenceLayer().invalidate_cache(None)
        DataPersistenceLayer().invalidate_cache(suffix)
        return Response(status=204, headers={"HX-Refresh": "true"})


def init(app: Flask):
    cache_bp = Blueprint("cache", __name__, url_prefix=f"{app.config['APPLICATION_ROOT']}/cache")

    cache_bp.add_url_rule("/invalidate", view_func=InvalidateCache.as_view("invalidate_cache"))
    cache_bp.add_url_rule("/invalidate/<string:suffix>", view_func=InvalidateCache.as_view("invalidate_cache_suffix"))

    app.register_blueprint(cache_bp)
