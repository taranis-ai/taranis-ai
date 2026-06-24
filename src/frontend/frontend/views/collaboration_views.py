from urllib.parse import unquote

from flask import flash, make_response, redirect, render_template, request, session, url_for
from flask.typing import ResponseReturnValue
from models.report import ReportItem
from werkzeug.exceptions import HTTPException

from frontend.auth import auth_required
from frontend.core_api import CoreApi
from frontend.data_persistence import DataPersistenceLayer
from frontend.views.base_view import BaseView


COLLAB_SESSION_CHANNELS_KEY = "collab_channels"
COLLAB_SESSION_CURRENT_KEY = "collab_current_channel"
COLLAB_SESSION_FINALIZE_RESULTS_KEY = "collab_finalize_results"


class CollaborationView:
    @staticmethod
    def _selected_story_id(active_channel: dict | None, selected_story_id: str | None) -> str:
        stories = (active_channel or {}).get("stories") or []
        if selected_story_id and any(story.get("id") == selected_story_id for story in stories):
            return selected_story_id
        focused_story_id = ((active_channel or {}).get("workspace") or {}).get("focused_story_id", "")
        if focused_story_id and any(story.get("id") == focused_story_id for story in stories):
            return focused_story_id
        if stories:
            return stories[0].get("id", "")
        return ""

    @staticmethod
    def _get_session_channels() -> list[str]:
        channels = session.get(COLLAB_SESSION_CHANNELS_KEY, [])
        return [channel for channel in channels if isinstance(channel, str) and channel]

    @classmethod
    def _set_session_channels(cls, channel_ids: list[str]) -> None:
        session[COLLAB_SESSION_CHANNELS_KEY] = list(dict.fromkeys(channel_ids))

    @classmethod
    def _remember_channel(cls, channel_id: str) -> None:
        channels = cls._get_session_channels()
        if channel_id not in channels:
            channels.append(channel_id)
        cls._set_session_channels(channels)
        session[COLLAB_SESSION_CURRENT_KEY] = channel_id

    @staticmethod
    def _get_finalize_results() -> dict[str, dict]:
        results = session.get(COLLAB_SESSION_FINALIZE_RESULTS_KEY, {})
        return results if isinstance(results, dict) else {}

    @classmethod
    def _set_finalize_result(cls, channel_id: str, finalize_result: dict) -> None:
        results = cls._get_finalize_results()
        results[channel_id] = finalize_result
        session[COLLAB_SESSION_FINALIZE_RESULTS_KEY] = results

    @classmethod
    def _get_finalize_result(cls, channel_id: str | None) -> dict:
        if not channel_id:
            return {}
        return cls._get_finalize_results().get(channel_id, {})

    @classmethod
    def _forget_channel(cls, channel_id: str) -> None:
        remaining = [cid for cid in cls._get_session_channels() if cid != channel_id]
        cls._set_session_channels(remaining)
        if session.get(COLLAB_SESSION_CURRENT_KEY) == channel_id:
            session[COLLAB_SESSION_CURRENT_KEY] = remaining[0] if remaining else ""
        results = cls._get_finalize_results()
        if channel_id in results:
            results.pop(channel_id, None)
            session[COLLAB_SESSION_FINALIZE_RESULTS_KEY] = results

    @staticmethod
    def _notification_response(core_response) -> str:
        return BaseView.get_notification_from_response(core_response, oob=False)

    @classmethod
    def _load_workspace_context(
        cls,
        active_channel_id: str | None = None,
        notification: str | None = None,
        finalize_result: dict | None = None,
    ) -> dict:
        api = CoreApi()
        channels_payload = api.get_collaboration_channels() or {"items": []}
        channels = channels_payload.get("items", [])
        known_ids = [item.get("channel_id") for item in channels if item.get("status") == "open" and item.get("channel_id")]
        cls._set_session_channels([channel_id for channel_id in cls._get_session_channels() if channel_id in known_ids])

        active_id = active_channel_id or request.args.get("channel_id") or session.get(COLLAB_SESSION_CURRENT_KEY) or ""
        if not active_id and channels:
            active_id = channels[0].get("channel_id", "")

        active_channel = api.get_collaboration_channel(active_id) if active_id else None
        if active_channel and active_channel.get("status") == "open":
            cls._remember_channel(active_id)
        elif active_id:
            cls._forget_channel(active_id)
            active_channel = None

        selected_story_id = cls._selected_story_id(active_channel, request.args.get("story_id", ""))
        selected_story = next(
            (story for story in (active_channel or {}).get("stories", []) if story.get("id") == selected_story_id),
            None,
        )

        return {
            "_show_sidebar": False,
            "is_room_view": bool(active_channel_id),
            "channels": channels,
            "active_channel": active_channel,
            "active_channel_id": active_id if active_channel else "",
            "selected_story": selected_story,
            "selected_story_id": selected_story_id,
            "notification_html": notification or "",
            "finalize_result": finalize_result or cls._get_finalize_result(active_id),
        }

    @classmethod
    def _render_workspace(
        cls,
        active_channel_id: str | None = None,
        notification: str | None = None,
        finalize_result: dict | None = None,
    ) -> tuple[str, int]:
        context = cls._load_workspace_context(active_channel_id, notification, finalize_result)
        return render_template("collaboration/index.html", **context), 200

    @classmethod
    @auth_required()
    def workspace(cls, channel_id: str | None = None) -> tuple[str, int]:
        return cls._render_workspace(channel_id)

    @classmethod
    @auth_required()
    def dialog(cls) -> tuple[str, int]:
        story_ids = request.args.getlist("story_ids")
        if not story_ids and (story_id := request.args.get("story_id", "")):
            story_ids = [story_id]
        topic = request.args.get("topic", "")
        force_new = request.args.get("force_new", "").strip().lower() in {"1", "true", "yes"}
        channels_payload = CoreApi().get_collaboration_channels() or {"items": []}
        open_channels = [item for item in channels_payload.get("items", []) if item.get("status") == "open"]
        return render_template(
            "collaboration/dialog.html",
            story_ids=story_ids,
            topic=topic,
            open_channels=open_channels,
            current_channel_id="" if force_new else session.get(COLLAB_SESSION_CURRENT_KEY, ""),
        ), 200

    @classmethod
    @auth_required()
    def submit_dialog(cls) -> ResponseReturnValue:
        story_ids = request.form.getlist("story_ids")
        channel_id = request.form.get("channel_id", "").strip()
        api = CoreApi()
        try:
            if channel_id:
                if not story_ids:
                    return make_response(
                        BaseView.render_response_notification(
                            {"error": "Select one or more stories in Assess before adding them to a channel."}
                        ),
                        400,
                    )
                core_response = api.add_stories_to_collaboration(channel_id, story_ids)
                target_channel_id = channel_id
            else:
                topic = request.form.get("topic", "").strip()
                if not topic:
                    return make_response(BaseView.render_response_notification({"error": "Topic is required."}), 400)
                core_response = api.create_collaboration_channel(topic, story_ids)
                target_channel_id = core_response.json().get("channel_id", "") if core_response.ok else ""
        except HTTPException:
            raise
        except Exception:
            return make_response(BaseView.render_response_notification({"error": "Failed to update collaboration channel."}), 500)

        notification_html = cls._notification_response(core_response)
        if not core_response.ok or not target_channel_id:
            return make_response(notification_html, getattr(core_response, "status_code", 500) or 500)

        cls._remember_channel(target_channel_id)
        redirect_target = url_for("collaboration.workspace_channel", channel_id=target_channel_id)
        if request.headers.get("HX-Request") == "true":
            response = make_response(notification_html, 200)
            response.headers["HX-Redirect"] = redirect_target
            return response
        return redirect(redirect_target, code=302)

    @classmethod
    @auth_required()
    def join(cls) -> ResponseReturnValue:
        owner_base_url = unquote(request.args.get("owner_base_url", ""))
        channel_id = request.args.get("channel_id", "")
        token = request.args.get("token", "")
        if not owner_base_url or not channel_id or not token:
            flash("Invalid collaboration invite.", "error")
            return redirect(url_for("collaboration.workspace"))

        api = CoreApi()
        try:
            core_response = api.redeem_collaboration_invite(owner_base_url, channel_id, token)
        except HTTPException:
            raise
        except Exception:
            flash("Failed to redeem collaboration invite.", "error")
            return redirect(url_for("collaboration.workspace"))

        if not core_response.ok:
            BaseView.add_flash_notification(core_response)
            return redirect(url_for("collaboration.workspace"))

        cls._remember_channel(channel_id)
        flash("Joined collaboration channel.", "success")
        return redirect(url_for("collaboration.workspace_channel", channel_id=channel_id))

    @classmethod
    @auth_required()
    def finalize(cls, channel_id: str) -> tuple[str, int]:
        api = CoreApi()
        core_response = api.finalize_collaboration_channel(channel_id)
        BaseView.add_flash_notification(core_response)
        if core_response.ok:
            cls._set_finalize_result(channel_id, core_response.json())
        response = redirect(url_for("collaboration.workspace_channel", channel_id=channel_id), code=302)
        return response

    @classmethod
    @auth_required()
    def report_dialog(cls, channel_id: str) -> tuple[str, int] | ResponseReturnValue:
        api = CoreApi()
        core_response = api.finalize_collaboration_channel(channel_id)
        if not core_response.ok:
            BaseView.add_flash_notification(core_response)
            return redirect(url_for("collaboration.workspace_channel", channel_id=channel_id), code=302)

        finalize_result = core_response.json()
        cls._set_finalize_result(channel_id, finalize_result)
        reports = DataPersistenceLayer().get_objects(ReportItem)
        return (
            render_template(
                "assess/story_report_dialog.html",
                story_ids=finalize_result.get("report_story_ids", []),
                reports=reports,
                target="#collaboration-workspace",
                submit_url=url_for("collaboration.submit_report_dialog"),
                new_report_url=url_for("analyze.report", report_id="0")
                + "?"
                + "&".join(f"story_ids={story_id}" for story_id in finalize_result.get("report_story_ids", [])),
                channel_id=channel_id,
            ),
            200,
        )

    @classmethod
    @auth_required()
    def submit_report_dialog(cls) -> ResponseReturnValue:
        story_ids = request.form.getlist("story_ids")
        report_id = request.form.get("report", "").strip()
        channel_id = request.form.get("channel_id", "").strip()
        core_response = CoreApi().add_collaboration_stories_to_report(report_id, story_ids)
        BaseView.add_flash_notification(core_response)
        return BaseView.redirect_htmx(url_for("collaboration.workspace_channel", channel_id=channel_id))

    @classmethod
    @auth_required()
    def update_story(cls, channel_id: str, snapshot_id: str) -> ResponseReturnValue:
        payload = {
            "title": request.form.get("title", "").strip(),
            "description": request.form.get("description", "").strip(),
            "summary": request.form.get("summary", "").strip(),
            "comments": request.form.get("comments", "").strip(),
        }
        core_response = CoreApi().update_collaboration_story(channel_id, snapshot_id, payload)
        BaseView.add_flash_notification(core_response)
        return redirect(url_for("collaboration.workspace_channel", channel_id=channel_id, story_id=snapshot_id), code=302)

    @classmethod
    @auth_required()
    def move_news_item(cls, channel_id: str, snapshot_id: str, news_item_id: str) -> ResponseReturnValue:
        target_snapshot_id = request.form.get("target_snapshot_id", "").strip()
        core_response = CoreApi().move_collaboration_news_item(channel_id, snapshot_id, target_snapshot_id, news_item_id)
        BaseView.add_flash_notification(core_response)
        return redirect(url_for("collaboration.workspace_channel", channel_id=channel_id, story_id=snapshot_id), code=302)

    @classmethod
    @auth_required()
    def close(cls, channel_id: str) -> ResponseReturnValue:
        api = CoreApi()
        core_response = api.close_collaboration_channel(channel_id)
        BaseView.add_flash_notification(core_response)
        if core_response.ok:
            cls._forget_channel(channel_id)
        next_channel = session.get(COLLAB_SESSION_CURRENT_KEY) or ""
        if next_channel:
            return redirect(url_for("collaboration.workspace_channel", channel_id=next_channel), code=302)
        return redirect(url_for("collaboration.workspace"), code=302)
