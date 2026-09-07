import uuid
from copy import deepcopy
from typing import Any

from flask import abort, current_app, make_response, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue
from flask_jwt_extended import current_user
from models.assess import Story
from models.product import Product
from models.report import ReportItem, ReportTypes
from werkzeug.exceptions import HTTPException

from frontend.auth import auth_required
from frontend.cache import cache
from frontend.cache_models import PagingData
from frontend.core_api import CoreApi
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.utils.router_helpers import is_htmx_request
from frontend.views.base_view import BaseView


ANALYST_REVIEW_TIMEOUT_SECONDS = 4 * 60 * 60
ANALYST_REVIEW_PERMISSIONS = {
    "ASSESS_ACCESS",
    "ASSESS_UPDATE",
    "ANALYZE_ACCESS",
    "ANALYZE_CREATE",
    "ANALYZE_UPDATE",
    "PUBLISH_ACCESS",
    "PUBLISH_CREATE",
}


class AnalystReviewView:
    @staticmethod
    def has_permissions() -> bool:
        return ANALYST_REVIEW_PERMISSIONS.issubset(set(current_user.permissions or []))

    @classmethod
    def _require_permissions(cls) -> None:
        if not cls.has_permissions():
            abort(403)

    @staticmethod
    def _cache_key(run_id: str) -> str:
        return f"{cache.key_prefix}:analyst-review:{current_user.username}:{run_id}"

    @staticmethod
    def _testing_state_store() -> dict[str, dict[str, Any]] | None:
        if not current_app.testing:
            return None
        return current_app.extensions.setdefault("analyst_review_states", {})

    @classmethod
    def _load_state(cls, run_id: str) -> dict[str, Any] | None:
        key = cls._cache_key(run_id)
        state = cache.get(key)
        if state is None and (testing_store := cls._testing_state_store()) is not None:
            state = deepcopy(testing_store.get(key))
        if not isinstance(state, dict):
            return None
        if not isinstance(state.get("story_ids"), list) or not isinstance(state.get("report_id"), str):
            return None
        return state

    @classmethod
    def _store_state(cls, run_id: str, state: dict[str, Any]) -> bool:
        if not cache.enabled and (testing_store := cls._testing_state_store()) is not None:
            testing_store[cls._cache_key(run_id)] = deepcopy(state)
            return True
        return cache.set(cls._cache_key(run_id), state, timeout=ANALYST_REVIEW_TIMEOUT_SECONDS)

    @classmethod
    def _delete_state(cls, run_id: str) -> None:
        key = cls._cache_key(run_id)
        cache.delete(key)
        if (testing_store := cls._testing_state_store()) is not None:
            testing_store.pop(key, None)

    @staticmethod
    def _notification_from_response(response: Any) -> dict[str, Any]:
        try:
            payload = response.json()
        except Exception:
            payload = None
        if isinstance(payload, dict):
            return BaseView.get_notification_from_dict(payload)
        return {"message": "The review action failed.", "error": True}

    @classmethod
    def _start_context(cls, notification: dict[str, Any] | None = None) -> dict[str, Any]:
        reports: list[ReportItem] = []
        report_types: list[ReportTypes] = []
        try:
            dpl = DataPersistenceLayer()
            reports = list(dpl.get_objects(ReportItem, PagingData(query_params={"completed": "false"}).set_fetch_all()))
            report_types = list(dpl.get_objects(ReportTypes))
        except HTTPException:
            raise
        except Exception:
            logger.exception("Failed to load analyst review start options")
            notification = notification or {"message": "Unable to load reports for analyst review.", "error": True}

        type_review_defaults = {str(report_type.id): report_type.needs_review for report_type in report_types if report_type.id}
        report_review_defaults = {
            str(report.id): type_review_defaults.get(str(report.report_item_type_id), False) for report in reports if report.id
        }
        return {
            "_show_sidebar": False,
            "notification": notification,
            "reports": reports,
            "report_types": report_types,
            "report_review_defaults": report_review_defaults,
            "type_review_defaults": type_review_defaults,
        }

    @classmethod
    def _render_start(cls, notification: dict[str, Any] | None = None, status: int = 200) -> tuple[str, int]:
        return render_template("analyst_review/start.html", **cls._start_context(notification)), status

    @staticmethod
    def _existing_report(report_id: str) -> tuple[ReportItem | None, dict[str, Any] | None]:
        if not report_id:
            return None, {"message": "Choose an incomplete report.", "error": True}
        payload = CoreApi().api_get(f"/analyze/report-items/{report_id}")
        if not isinstance(payload, dict):
            return None, {"message": "The selected report is unavailable.", "error": True}
        report = ReportItem.model_validate(payload)
        if report.completed:
            return None, {"message": "Choose an incomplete report.", "error": True}
        return report, None

    @staticmethod
    def _new_report(title: str, report_type_id: str) -> tuple[ReportItem | None, dict[str, Any] | None]:
        if not title.strip() or not report_type_id:
            return None, {"message": "Enter a title and choose a report type.", "error": True}

        response = DataPersistenceLayer().store_object(
            ReportItem(title=title.strip(), report_item_type_id=report_type_id, completed=False, stories=[])
        )
        if not response.ok:
            return None, AnalystReviewView._notification_from_response(response)

        try:
            payload = response.json().get("report")
            report = ReportItem.model_validate(payload)
        except Exception:
            logger.exception("Core returned an invalid report after analyst review creation")
            return None, {"message": "Unable to create the report.", "error": True}

        DataPersistenceLayer().invalidate_model_cache_locally(ReportItem)
        return report, None

    @classmethod
    def _selected_report(cls) -> tuple[ReportItem | None, dict[str, Any] | None]:
        if request.form.get("mode") == "existing":
            return cls._existing_report(request.form.get("report_id", ""))
        if request.form.get("mode") == "new":
            return cls._new_report(request.form.get("title", ""), request.form.get("report_item_type_id", ""))
        return None, {"message": "Choose or create a report.", "error": True}

    @classmethod
    @auth_required()
    def start(cls) -> ResponseReturnValue:
        cls._require_permissions()
        if request.method == "GET":
            return cls._render_start()

        try:
            report, error = cls._selected_report()
            if error or not report or not report.id:
                return cls._render_start(error or {"message": "Unable to start analyst review.", "error": True}, 400)

            snapshot = CoreApi().api_get("/assess/analyst-review/snapshot")
            story_ids = snapshot.get("story_ids") if isinstance(snapshot, dict) else None
            if not isinstance(story_ids, list) or not all(isinstance(story_id, str) for story_id in story_ids):
                return cls._render_start({"message": "Unable to create the review queue.", "error": True}, 503)

            run_id = str(uuid.uuid7())
            state = {
                "report_id": report.id,
                "report_title": report.title or "Report",
                "story_ids": story_ids,
                "total": len(story_ids),
                "reviewed": 0,
                "added": 0,
                "review_report": request.form.get("review_report") == "true",
            }
            if not cls._store_state(run_id, state):
                return cls._render_start({"message": "Unable to save the review queue.", "error": True}, 503)
            return redirect(url_for("assess.analyst_review", run_id=run_id))
        except HTTPException:
            raise
        except Exception:
            logger.exception("Failed to start analyst review")
            return cls._render_start({"message": "Unable to start analyst review.", "error": True}, 500)

    @classmethod
    def _load_current_story(cls, run_id: str, state: dict[str, Any]) -> Story | None:
        while state["story_ids"]:
            story_id = state["story_ids"][0]
            story = DataPersistenceLayer().get_object(Story, story_id)
            if story:
                return story
            state["story_ids"].pop(0)
            state["reviewed"] += 1
            if not cls._store_state(run_id, state):
                return None
        return None

    @staticmethod
    def _report_needs_review(report: ReportItem) -> bool:
        return any(
            attribute.type == "STORY" or (attribute.required and not str(attribute.value or "").strip())
            for group in report.grouped_attributes or []
            for attribute in group.attributes
        )

    @staticmethod
    def _publish_url(report_id: str) -> str:
        try:
            matching_products = [
                product for product in DataPersistenceLayer().get_objects(Product) if report_id in product.report_items and product.id
            ]
        except HTTPException:
            raise
        except Exception:
            logger.exception(f"Failed to find products for analyst review report {report_id}")
            matching_products = []

        if len(matching_products) == 1:
            return url_for("publish.product", product_id=matching_products[0].id)
        return url_for("publish.product", product_id="0", report_id=report_id)

    @classmethod
    def _completion_url(cls, run_id: str, state: dict[str, Any]) -> str:
        report = DataPersistenceLayer().get_object(ReportItem, state["report_id"])
        if not report or not report.id:
            abort(404)
        if state["review_report"] or cls._report_needs_review(report):
            return url_for("analyze.report", report_id=report.id, review_run=run_id)

        target = cls._publish_url(report.id)
        cls._delete_state(run_id)
        return target

    @classmethod
    def report_review_state(cls, run_id: str, report_id: str) -> dict[str, Any] | None:
        state = cls._load_state(run_id)
        if not state or state["story_ids"] or state["report_id"] != report_id:
            return None
        return state

    @classmethod
    def complete_report_review(cls, run_id: str, report_id: str) -> str | None:
        if not cls.report_review_state(run_id, report_id):
            return None
        target = cls._publish_url(report_id)
        cls._delete_state(run_id)
        return target

    @classmethod
    def _review_context(cls, run_id: str, state: dict[str, Any], story: Story) -> dict[str, Any]:
        return {
            "_show_sidebar": False,
            "run_id": run_id,
            "review": state,
            "story": story,
        }

    @classmethod
    def _render_review_partial(
        cls,
        run_id: str,
        state: dict[str, Any],
        story: Story,
        notification: dict[str, Any] | None = None,
        status: int = 200,
    ) -> ResponseReturnValue:
        notification_html = render_template("notification/index.html", notification=notification) if notification else ""
        content = render_template("analyst_review/_review.html", **cls._review_context(run_id, state, story))
        return make_response(notification_html + content, status)

    @classmethod
    @auth_required()
    def review(cls, run_id: str) -> ResponseReturnValue:
        cls._require_permissions()
        state = cls._load_state(run_id)
        if not state:
            return render_template("errors/404.html", error="This analyst review has expired."), 404

        story = cls._load_current_story(run_id, state)
        if not story:
            return BaseView.redirect_htmx(cls._completion_url(run_id, state))
        return render_template("analyst_review/review.html", **cls._review_context(run_id, state, story)), 200

    @classmethod
    @auth_required()
    def apply_action(cls, run_id: str) -> ResponseReturnValue:
        cls._require_permissions()
        state = cls._load_state(run_id)
        if not state:
            return render_template("errors/404.html", error="This analyst review has expired."), 404

        story = cls._load_current_story(run_id, state)
        if not story:
            return BaseView.redirect_htmx(cls._completion_url(run_id, state))

        action = request.form.get("action", "")
        if action not in {"add", "dismiss", "skip"}:
            return cls._render_review_partial(
                run_id,
                state,
                story,
                {"message": "Choose Add, Dismiss, or Skip.", "error": True},
                400,
            )

        if action != "skip":
            payload = {"story_id": story.id, "action": action}
            if action == "add":
                payload["report_id"] = state["report_id"]
            response = CoreApi().api_post("/assess/analyst-review/actions", json_data=payload)
            if not response.ok:
                return cls._render_review_partial(
                    run_id,
                    state,
                    story,
                    cls._notification_from_response(response),
                    response.status_code or 500,
                )

            dpl = DataPersistenceLayer()
            dpl.invalidate_model_cache_locally(Story, story.id)
            if action == "add":
                dpl.invalidate_model_cache_locally(ReportItem, state["report_id"])

        previous_state = deepcopy(state)
        state["story_ids"].pop(0)
        state["reviewed"] += 1
        if action == "add":
            state["added"] += 1
        if not cls._store_state(run_id, state):
            logger.error(f"Failed to advance analyst review run {run_id}")
            return cls._render_review_partial(
                run_id,
                previous_state,
                story,
                {"message": "The review queue could not advance.", "error": True},
                503,
            )

        if not state["story_ids"]:
            return BaseView.redirect_htmx(cls._completion_url(run_id, state))

        next_story = cls._load_current_story(run_id, state)
        if not next_story:
            return BaseView.redirect_htmx(cls._completion_url(run_id, state))
        if is_htmx_request():
            return cls._render_review_partial(run_id, state, next_story)
        return redirect(url_for("assess.analyst_review", run_id=run_id))
