from typing import Any
from uuid import UUID

from flask import abort, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue
from flask_jwt_extended import current_user
from models.discussion import COMMENT_MAX_LENGTH, DISCUSSION_PERMISSIONS, DiscussionKind
from requests import RequestException
from werkzeug.datastructures import MultiDict

from frontend.auth import auth_required
from frontend.core_api import CoreApi
from frontend.log import logger
from frontend.utils.router_helpers import is_htmx_request


LABELS: dict[DiscussionKind, tuple[str, str]] = {"story": ("Story", "Stories"), "report": ("Report", "Reports"), "product": ("Product", "Products")}
PERMISSIONS = list(DISCUSSION_PERMISSIONS.values())


def _page(values: MultiDict[str, str]) -> int:
    return max(1, min(100000, values.get("page", 1, type=int)))


def _scope(values: MultiDict[str, str]) -> str | None:
    scope = values.get("scope")
    return scope if scope in LABELS else None


def _load(endpoint: str, params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    # Comment access and activity are evaluated live, independent of cached parent pages.
    try:
        response = CoreApi().api_get_response(endpoint, params)
        if response.ok:
            return response.json(), 200
        if response.status_code in {401, 403, 404}:
            return {}, response.status_code
        logger.warning(f"Discussion lookup failed with HTTP {response.status_code}")
    except RequestException, ValueError:
        logger.exception("Discussion lookup failed")
    return {}, 502


def _endpoint(kind: str, parent_id: str) -> str:
    if kind not in LABELS:
        abort(404)
    try:
        canonical_id = str(UUID(parent_id))
    except ValueError:
        abort(404)
    return f"/discussions/{kind}/{canonical_id}"


def _detail_url(kind: str, parent_id: str) -> str:
    if kind == "story":
        return url_for("assess.story", story_id=parent_id)
    if kind == "report":
        return url_for("analyze.report", report_id=parent_id)
    return url_for("publish.product", product_id=parent_id)


def _section(kind: str, parent_id: str, *, preview: bool, page: int, scope: str | None) -> tuple[dict[str, Any], int]:
    params = {"preview": "true"} if preview else {"page": page}
    discussion, status = _load(_endpoint(kind, parent_id), params)
    thread_args = {"kind": kind, "parent_id": parent_id, "scope": scope}
    return {
        "discussion": discussion,
        "discussion_preview": preview,
        "load_error": status != 200,
        "comment_max_length": COMMENT_MAX_LENGTH,
        "discussion_thread_url": url_for("discussion.thread", **thread_args),
        "retry_url": url_for("discussion.thread", **thread_args, preview=1 if preview else None, page=page if page > 1 else None),
        "comment_action": url_for("discussion.post_comment", kind=kind, parent_id=parent_id),
        "discussion_page": page,
        "discussion_scope": scope,
        "discussion_kind": kind,
        "discussion_parent_id": parent_id,
        "has_older_comments": discussion.get("total_count", 0) > page * 20,
    }, status


def discussion_preview(kind: str, parent_id: str) -> dict[str, Any] | None:
    try:
        UUID(parent_id)
    except ValueError:
        return None
    context, _ = _section(kind, parent_id, preview=True, page=1, scope=kind)
    return context


@auth_required(PERMISSIONS)
def overview() -> ResponseReturnValue:
    scope = _scope(request.args)
    page = _page(request.args)
    items, status = _load("/discussions", {"kind": scope, "page": page})
    return render_template(
        "discussion/overview.html",
        _show_sidebar=False,
        filters={kind: label[1] for kind, label in LABELS.items() if DISCUSSION_PERMISSIONS[kind] in (current_user.permissions or [])},
        discussion_labels=LABELS,
        discussion_scope=scope,
        discussions=items.get("items", []),
        discussion_page=page,
        has_more=items.get("has_more", False),
        load_error=status != 200,
    ), status


def _full_thread(context: dict[str, Any]) -> str:
    kind = context["discussion_kind"]
    return render_template(
        "discussion/thread.html",
        _show_sidebar=False,
        parent_label=LABELS[kind][0],
        parent_url=_detail_url(kind, context["discussion_parent_id"]),
        **context,
    )


@auth_required(PERMISSIONS)
def thread(kind: str, parent_id: str) -> ResponseReturnValue:
    preview = is_htmx_request() and request.args.get("preview") == "1"
    context, status = _section(kind, parent_id, preview=preview, page=_page(request.args), scope=_scope(request.args))
    if not preview and status == 404:
        abort(404)
    if preview:
        return render_template("discussion/section.html", **context), status
    return _full_thread(context), status


@auth_required(PERMISSIONS)
def post_comment(kind: str, parent_id: str) -> ResponseReturnValue:
    endpoint = _endpoint(kind, parent_id)
    scope = _scope(request.form)
    preview = request.form.get("preview") == "1"
    page = _page(request.form)
    action = request.form.get("action", "post")
    draft = request.form.get("body", "")
    comment_id = request.form.get("comment_id", "")
    if action in {"edit", "delete"}:
        try:
            endpoint = f"{endpoint}/{UUID(comment_id)}"
        except ValueError:
            abort(404)
    elif action != "post":
        abort(400)

    message = ""
    status = 200
    try:
        api = CoreApi()
        if action == "post":
            response = api.api_post(endpoint, json_data={"body": draft})
        elif action == "edit":
            response = api.api_patch(endpoint, json_data={"body": draft})
        else:
            response = api.api_delete(endpoint)
        if not response.ok:
            status = response.status_code if response.status_code in {400, 403, 404} else 502
            message = {
                400: f"Enter a comment of 1 to {COMMENT_MAX_LENGTH:,} characters.",
                403: "You do not have permission to make this change.",
                404: "That comment or discussion is no longer available.",
            }.get(status, "Could not save this change. Try again.")
    except RequestException:
        logger.exception("Comment action failed")
        message, status = "Could not reach the server. Try again.", 502

    htmx = is_htmx_request()
    if message and htmx:
        return render_template("discussion/action_error.html", action_error=message), status
    if not message:
        if action == "post":
            page = 1
        if not htmx:
            return redirect(
                url_for("discussion.thread", kind=kind, parent_id=parent_id, scope=scope, page=page, _anchor="comments"), code=303
            )

    context, _ = _section(kind, parent_id, preview=preview and htmx, page=page, scope=scope)
    if page > 1 and (discussion := context["discussion"]) and not discussion["items"]:
        page = max(1, (discussion["total_count"] + 19) // 20)
        context, _ = _section(kind, parent_id, preview=False, page=page, scope=scope)
    if message:
        context.update(failed_action=action, failed_comment_id=comment_id, action_error=message, comment_draft=draft)
        return _full_thread(context), status

    context["action_status"] = {"post": "Comment posted.", "edit": "Comment updated.", "delete": "Comment deleted."}[action]
    # The change succeeded even if reloading failed. Keep the success status visible and offer a reload.
    return render_template("discussion/section.html", **context), 200
