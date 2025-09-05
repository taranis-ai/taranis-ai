from flask import Flask, Blueprint

from frontend.views.product_views import ProductView


def init(app: Flask):
    publish_bp = Blueprint("publish", __name__, url_prefix=f"{app.config['APPLICATION_ROOT']}")

    publish_bp.add_url_rule("/publish", view_func=ProductView.as_view("publish"))
    publish_bp.add_url_rule("/publish/<string:product_id>", view_func=ProductView.as_view("product"))
    publish_bp.add_url_rule("/product/<string:product_id>", view_func=ProductView.as_view("product_"))

    app.register_blueprint(publish_bp)
