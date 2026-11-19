from typing import Any
from urllib.parse import urlencode

import requests
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from frontend.auth import auth_required
from frontend.core_api import CoreApi


def init(app):
    bp = Blueprint("social", __name__, url_prefix=app.config["APPLICATION_ROOT"])

    @bp.get("/assess/social")
    @auth_required("ASSESS_ACCESS")
    def monitor():
        filters: dict[str, Any] = request.args.to_dict()
        filters["sources"] = request.args.getlist("sources")
        data = CoreApi().api_get("/assess/social", params=filters)
        if data is None:
            abort(502)
        return render_template("social/monitor.html", **data, filters=filters, _show_sidebar=False)

    @bp.post("/assess/social/beats")
    @auth_required("ASSESS_ACCESS")
    def save_beat():
        filters = {
            "sources": request.form.getlist("sources"),
            "search": request.form.get("search", ""),
            "images": request.form.get("images") == "true",
        }
        if platform := request.form.get("platform"):
            filters["platform"] = platform
        response = CoreApi().api_post("/assess/social/beats", {**filters, "name": request.form.get("name", "")})
        if not response.ok:
            abort(response.status_code)
        return redirect(url_for("social.monitor") + "?" + urlencode(filters, doseq=True))

    @bp.get("/assess/social/thread/<uuid:post_id>")
    @auth_required("ASSESS_ACCESS")
    def thread(post_id):
        page = max(0, request.args.get("page", 0, type=int))
        data = CoreApi().api_get(f"/assess/social/posts/{post_id}", {"page": page})
        if data is None:
            abort(404)
        return render_template("social/thread.html", **data, root_id=post_id, page=page, fragment=bool(request.headers.get("HX-Request")))

    @bp.get("/assess/social/material/<uuid:item_id>")
    @auth_required("ASSESS_ACCESS")
    def material(item_id):
        post = CoreApi().api_get(f"/assess/social/material/{item_id}")
        return render_template("social/material.html", post=post, fragment=bool(request.headers.get("HX-Request")))

    @bp.get("/assess/social/images/<uuid:image_id>")
    @auth_required("ASSESS_ACCESS")
    def image(image_id):
        api = CoreApi()
        response = api.api_download(f"/assess/social/images/{image_id}", {"size": request.args.get("size", "")})
        if not response.ok:
            status = response.status_code
            response.close()
            abort(status)
        result = api.stream_proxy(response, "image")
        result.headers["Cache-Control"] = "private, no-store"
        return result

    @bp.get("/assess/social/story-choices")
    @auth_required("ASSESS_ACCESS")
    def story_choices():
        data = CoreApi().get_stories({"search": request.args.get("story_search", ""), "limit": 30, "no_count": "true"})
        if data is None:
            abort(502)
        return render_template("social/story_choices.html", stories=data["items"])

    @bp.post("/assess/social/attach")
    @auth_required("ASSESS_ACCESS")
    def attach():
        data = {
            "posts": list(dict.fromkeys(request.form.getlist("posts"))),
            "title": request.form.get("title", ""),
            "story_id": request.form.get("story_id", ""),
        }
        result = CoreApi().api_post("/assess/social/attach", data)
        if not result.ok:
            return render_template(
                "social/attach_result.html", error="Could not attach the selection. Check the destination and access."
            ), result.status_code
        story_id = result.json()["id"]
        if not request.headers.get("HX-Request"):
            return redirect(url_for("assess.story", story_id=story_id))
        return render_template("social/attach_result.html", story_id=story_id, attached=data["posts"]), 200, {"HX-Trigger": "social-attached"}

    @bp.route("/analyze/report/<uuid:report_id>/figures", methods=["GET", "POST"])
    @auth_required("ANALYZE_ACCESS")
    def figures(report_id):
        api = CoreApi()
        endpoint = f"/analyze/reports/{report_id}/figures"
        error = None
        status = 200
        if request.method == "POST":
            ids = sorted(request.form.getlist("image_id"), key=lambda i: request.form.get("order-" + i, 1, type=int))
            data = [{"image_id": i, "caption": request.form.get("caption-" + i, ""), "alt": request.form.get("alt-" + i, "")} for i in ids]
            response = api.api_put(endpoint, {"figures": data})
            if response.ok:
                flash("Report figures saved", "success")
                return redirect(url_for("social.figures", report_id=report_id))
            status = response.status_code
            error = "Figures could not be saved. Check source access and publication eligibility."
        payload = api.api_get(endpoint)
        if payload is None:
            abort(404)
        return render_template("social/figures.html", images=payload["images"], report_id=report_id, error=error, _show_sidebar=False), status

    @bp.errorhandler(requests.RequestException)
    def unavailable(_error):
        return "The social monitor service is unavailable.", 502

    app.register_blueprint(bp)
