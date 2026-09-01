from flask import Blueprint, Flask

from frontend.views.collaboration_views import CollaborationDocumentView, CollaborationView


def init(app: Flask):
    bp = Blueprint("collaboration", __name__, url_prefix=f"{app.config['APPLICATION_ROOT']}")
    bp.add_url_rule("/collaboration", view_func=CollaborationView.as_view("workspace"))
    bp.add_url_rule("/collaboration/<string:action>", view_func=CollaborationView.as_view("action"), methods=["POST"])
    bp.add_url_rule("/collaboration/<string:channel_id>", view_func=CollaborationView.as_view("channel"))
    bp.add_url_rule("/collaboration/documents/<string:document_id>", view_func=CollaborationDocumentView.as_view("document"))
    app.register_blueprint(bp)
