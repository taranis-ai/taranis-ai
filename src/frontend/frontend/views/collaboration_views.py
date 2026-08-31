from flask import redirect, render_template, request, url_for
from flask.views import MethodView

from frontend.auth import auth_required
from frontend.core_api import CoreApi


class CollaborationDocumentView(MethodView):
    decorators = [auth_required()]

    def get(self, document_id: str):
        return render_template("collaboration/document.html", document_id=document_id)


class CollaborationStoryDialogView(MethodView):
    decorators = [auth_required()]

    def get(self):
        channels = CoreApi().api_get("/collaboration/channels") or {}
        story_ids = [value.strip() for value in request.args.get("story_ids", "").split(",") if value.strip()]
        return render_template("collaboration/add_story_dialog.html", channels=channels.get("items", []), story_ids=story_ids)


class CollaborationView(MethodView):
    decorators = [auth_required()]

    def get(self, channel_id: str | None = None):
        channels = CoreApi().api_get("/collaboration/channels") or {}
        channel = CoreApi().api_get(f"/collaboration/channels/{channel_id}") if channel_id else None
        report_workspace = CoreApi().api_get(f"/collaboration/channels/{channel_id}/report-workspace") if channel_id else None
        create_story_ids = ",".join(value.strip() for value in request.args.get("story_ids", "").split(",") if value.strip())
        selected_story_id = request.args.get("story_id", "")
        return render_template(
            "collaboration/index.html",
            channels=channels.get("items", []),
            channel=channel,
            report_workspace=report_workspace or {},
            create_story_ids=create_story_ids,
            selected_story_id=selected_story_id,
        )

    def post(self, action: str):
        if action == "create":
            response = CoreApi().api_post(
                "/collaboration/channels",
                {"topic": request.form.get("topic", ""), "owner_base_url": request.host_url.rstrip("/")},
            )
        elif action == "add-stories":
            response = CoreApi().api_post(
                f"/collaboration/channels/{request.form.get('channel_id', '')}/stories",
                {"story_ids": [value.strip() for value in request.form.get("story_ids", "").split(",") if value.strip()]},
            )
        elif action == "remove-story":
            response = CoreApi().api_delete(
                f"/collaboration/channels/{request.form.get('channel_id', '')}/stories/{request.form.get('snapshot_id', '')}"
            )
        elif action in {"close", "finalize"}:
            endpoint = "close" if action == "close" else "finalize"
            response = CoreApi().api_post(f"/collaboration/channels/{request.form.get('channel_id', '')}/{endpoint}")
        elif action == "create-report":
            response = CoreApi().api_post(
                f"/collaboration/channels/{request.form.get('channel_id', '')}/report-drafts",
                {"report_item_type_id": request.form.get("report_item_type_id", ""), "title": request.form.get("title", "")},
            )
        elif action == "delete-report":
            response = CoreApi().api_delete(
                f"/collaboration/channels/{request.form.get('channel_id', '')}/report-drafts/{request.form.get('draft_id', '')}"
            )
        elif action == "finalize-report":
            response = CoreApi().api_post(
                f"/collaboration/channels/{request.form.get('channel_id', '')}/report-drafts/{request.form.get('draft_id', '')}/finalize"
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
        channel_id = request.form.get("channel_id") or ""
        return (
            redirect(url_for("collaboration.channel", channel_id=channel_id)) if channel_id else redirect(url_for("collaboration.workspace"))
        )
