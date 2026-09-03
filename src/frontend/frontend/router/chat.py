from flask import Blueprint, Flask

from frontend.views.chat_views import ChatView


def init(app: Flask):
    chat_bp = Blueprint("chat", __name__, url_prefix=app.config["APPLICATION_ROOT"])
    chat_bp.add_url_rule("/chat", view_func=ChatView.index, methods=["GET"], endpoint="index")
    chat_bp.add_url_rule("/chat/messages", view_func=ChatView.send_message, methods=["POST"], endpoint="send_message")
    chat_bp.add_url_rule("/chat/<string:conversation_id>", view_func=ChatView.index, methods=["GET"], endpoint="conversation")
    chat_bp.add_url_rule(
        "/chat/<string:conversation_id>",
        view_func=ChatView.delete_conversation,
        methods=["DELETE"],
        endpoint="delete_conversation",
    )
    chat_bp.add_url_rule(
        "/chat/<string:conversation_id>/messages",
        view_func=ChatView.send_message,
        methods=["POST"],
        endpoint="conversation_message",
    )
    app.register_blueprint(chat_bp)
