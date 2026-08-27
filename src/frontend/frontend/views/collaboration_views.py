from flask import redirect, render_template, request, url_for
from flask.views import MethodView

from frontend.auth import auth_required
from frontend.core_api import CoreApi


class CollaborationDocumentView(MethodView):
    decorators = [auth_required()]

    def get(self, document_id: str):
        return render_template("collaboration/document.html", document_id=document_id)


class CollaborationView(MethodView):
    decorators = [auth_required()]

    def get(self, channel_id: str | None = None):
        channels = CoreApi().api_get("/collaboration/channels") or {}
        channel = CoreApi().api_get(f"/collaboration/channels/{channel_id}") if channel_id else None
        return render_template("collaboration/index.html", channels=channels.get("items", []), channel=channel)

    def post(self, action: str):
        if action == "create":
            response = CoreApi().api_post(
                "/collaboration/channels", {"story_id": request.form.get("story_id", ""), "owner_base_url": request.host_url.rstrip("/")}
            )
        else:
            response = CoreApi().api_post(
                "/collaboration/channels/join",
                {
                    "channel_id": request.form.get("channel_id", ""),
                    "token": request.form.get("token", ""),
                    "owner_base_url": request.form.get("owner_base_url", ""),
                    "base_url": request.host_url.rstrip("/"),
                },
            )
        return redirect(url_for("collaboration.workspace")) if response and response.ok else redirect(url_for("collaboration.workspace"))
