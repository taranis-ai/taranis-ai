from datetime import datetime, timezone
from typing import Any

from flask import render_template, request
from flask.views import MethodView

from frontend.auth import auth_required
from frontend.cache_models import PagingData
from frontend.config import Config
from frontend.core_api import CoreApi
from frontend.data_persistence import DataPersistenceLayer
from frontend.utils.router_helpers import convert_query_params, is_htmx_request
from frontend.views.admin_views.admin_mixin import AdminMixin
from frontend.views.base_view import BaseView
from models.admin import Job
from models.task import Task


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except ValueError:
        return None


def _format_task_stats(raw_stats: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    formatted: dict[str, dict[str, Any]] = {}
    for task_name, stats in raw_stats.items():
        formatted[task_name] = stats.copy()
        formatted[task_name]["last_run"] = _parse_iso_datetime(stats.get("last_run"))
        formatted[task_name]["last_success"] = _parse_iso_datetime(stats.get("last_success"))
    return formatted


def _notification_error(message: str, status_code: int = 500) -> tuple[str, int]:
    return BaseView.render_response_notification({"message": message, "error": True}), status_code


class SchedulerView(AdminMixin, BaseView):
    model = Job
    icon = "calendar-days"
    htmx_list_template = "schedule/dashboard.html"
    htmx_update_template = "schedule/dashboard.html"
    default_template = "schedule/dashboard.html"
    base_route = "admin.scheduler"
    _read_only = True
    _index = 61
    allowed_tabs = {"scheduled", "active", "failed", "history"}

    @classmethod
    def _resolve_tab(cls, initial_tab: str | None) -> str:
        tab = (initial_tab or request.args.get("tab") or "scheduled").lower()
        match tab:
            case "scheduled" | "active" | "failed" | "history":
                return tab
            case _:
                return "scheduled"

    def get(self, initial_tab: str | None = None, **kwargs) -> tuple[str, int]:
        """Render the main scheduler dashboard"""
        try:
            selected_tab = self._resolve_tab(initial_tab)

            # Get scheduled jobs
            jobs_data = CoreApi().api_get("/config/schedule")
            jobs = jobs_data.get("items", []) if jobs_data else []

            # Get queue status
            queues_data = CoreApi().api_get("/config/workers/tasks")
            queues = queues_data if isinstance(queues_data, list) else []

            # Get worker stats
            worker_stats_data = CoreApi().api_get("/config/workers/stats")
            worker_stats = worker_stats_data if isinstance(worker_stats_data, dict) else None

            # Get task execution stats
            task_results = DataPersistenceLayer().get_objects(Task)
            stats_meta = getattr(task_results, "extra", {}) if task_results is not None else {}
            task_stats = _format_task_stats(stats_meta.get("task_stats", {}))
            totals = stats_meta.get("totals", {})
            total_successes = totals.get("successes", 0)
            total_failures = totals.get("failures", 0)
            overall_success_rate = totals.get("overall_success_rate", 0)

            # Get base context with sidebar and admin layout
            context = self._common_context()
            context.update(
                {
                    "jobs": jobs,
                    "queues": queues,
                    "worker_stats": worker_stats,
                    "task_results": task_results,
                    "task_stats": task_stats,
                    "total_successes": total_successes,
                    "total_failures": total_failures,
                    "overall_success_rate": overall_success_rate,
                    "initial_tab": selected_tab,
                }
            )

            return render_template("schedule/dashboard.html", **context), 200

        except Exception as e:
            from frontend.log import logger

            logger.exception(f"Failed to load scheduler dashboard: {e}")
            return render_template("errors/500.html", error=str(e)), 500


class ScheduleAPI(MethodView):
    @auth_required()
    def get(self):
        query_params = convert_query_params(request.args, PagingData)
        error = None
        result = None
        try:
            paging = PagingData(**query_params)
            result = DataPersistenceLayer().get_objects(Job, paging)
        except Exception as exc:  # pragma: no cover - defensive rendering path
            error = str(exc)

        return render_template("schedule/index.html", jobs=result, error=error)


class ScheduleJobsAPI(MethodView):
    """HTMX endpoint for scheduled jobs table"""

    @auth_required()
    def get(self):
        if not is_htmx_request():
            return SchedulerView().get(initial_tab="scheduled")
        try:
            jobs_data = CoreApi().api_get("/config/schedule")
            jobs = jobs_data.get("items", []) if jobs_data else []
            jobs.sort(key=lambda job: (job.get("next_run_time") is None, job.get("next_run_time") or ""))
            return render_template("schedule/jobs_table.html", jobs=jobs)
        except Exception as exc:  # pragma: no cover - defensive rendering path
            return _notification_error(f"Failed to load jobs: {exc}")


class ScheduleQueuesAPI(MethodView):
    """HTMX endpoint for queue status cards"""

    @auth_required()
    def get(self):
        if not is_htmx_request():
            return SchedulerView().get(initial_tab="scheduled")
        try:
            queues_data = CoreApi().api_get("/config/workers/tasks")
            queues = queues_data if isinstance(queues_data, list) else []

            worker_stats_data = CoreApi().api_get("/config/workers/stats")
            worker_stats = worker_stats_data if isinstance(worker_stats_data, dict) else None

            return render_template("schedule/queue_cards.html", queues=queues, worker_stats=worker_stats)
        except Exception as exc:  # pragma: no cover - defensive rendering path
            return _notification_error(f"Failed to load queues: {exc}")


class ScheduleActiveJobsAPI(MethodView):
    """HTMX endpoint for active jobs"""

    @auth_required()
    def get(self):
        if not is_htmx_request():
            return SchedulerView().get(initial_tab="active")
        try:
            active_jobs_data = CoreApi().api_get("/config/workers/active")
            active_jobs = active_jobs_data.get("items", []) if active_jobs_data else []
            active_jobs.sort(key=lambda job: job.get("started_at") or "")
            return render_template("schedule/active_jobs.html", active_jobs=active_jobs)
        except Exception as exc:  # pragma: no cover - defensive rendering path
            return _notification_error(f"Failed to load active jobs: {exc}")


class ScheduleFailedJobsAPI(MethodView):
    """HTMX endpoint for failed jobs"""

    @auth_required()
    def get(self):
        if not is_htmx_request():
            return SchedulerView().get(initial_tab="failed")
        try:
            failed_jobs_data = CoreApi().api_get("/config/workers/failed")
            failed_jobs = failed_jobs_data.get("items", []) if failed_jobs_data else []
            failed_jobs.sort(key=lambda job: job.get("failed_at") or "", reverse=True)
            return render_template("schedule/failed_jobs.html", failed_jobs=failed_jobs)
        except Exception as exc:  # pragma: no cover - defensive rendering path
            return _notification_error(f"Failed to load failed jobs: {exc}")


class ScheduleHistoryAPI(MethodView):
    """HTMX endpoint for execution history"""

    @auth_required()
    def get(self):
        if not is_htmx_request():
            return SchedulerView().get(initial_tab="history")
        try:
            task_results = DataPersistenceLayer().get_objects(Task)
            stats_meta = getattr(task_results, "extra", {}) if task_results is not None else {}
            raw_task_stats: dict[str, dict[str, Any]] = stats_meta.get("task_stats", {})
            totals = stats_meta.get("totals", {})
            total_successes = totals.get("successes", 0)
            total_failures = totals.get("failures", 0)
            overall_success_rate = totals.get("overall_success_rate", 0)

            formatted_task_stats = _format_task_stats(raw_task_stats)

            task_stats = dict(
                sorted(
                    formatted_task_stats.items(),
                    key=lambda item: item[1].get("last_run") or datetime.min,
                    reverse=True,
                )
            )

            return render_template(
                "schedule/execution_history.html",
                task_results=task_results,
                task_stats=task_stats,
                total_successes=total_successes,
                total_failures=total_failures,
                overall_success_rate=overall_success_rate,
            )
        except Exception as exc:  # pragma: no cover - defensive rendering path
            return _notification_error(f"Failed to load history: {exc}")


class ScheduleRetryJobAPI(MethodView):
    """HTMX endpoint to retry a failed job"""

    @auth_required()
    def post(self, job_id: str):
        try:
            response = CoreApi().api_post(f"/config/workers/failed/{job_id}/retry")
            if not response or not response.ok:
                error_message = "Unknown error"
                if response is not None:
                    try:
                        payload = response.json()
                        error_message = payload.get("error") or payload.get("message") or response.text
                    except Exception:
                        error_message = response.text

                status_code = response.status_code if response is not None else 500
                return _notification_error(f"Failed to retry job: {error_message}", status_code)

            failed_jobs_data = CoreApi().api_get("/config/workers/failed")
            failed_jobs = failed_jobs_data.get("items", []) if failed_jobs_data else []
            notification_html = BaseView.get_notification_from_response(response)
            table_html = render_template("schedule/failed_jobs.html", failed_jobs=failed_jobs)
            return notification_html + table_html
        except Exception as exc:  # pragma: no cover - defensive rendering path
            return _notification_error(f"Failed to retry job: {exc}")


class ScheduleJobDetailsAPI(MethodView):
    @auth_required()
    def get(self, job_id: str):
        job = DataPersistenceLayer().get_object(Job, job_id)
        if job is None:
            return f"Failed to fetch job from: {Config.TARANIS_CORE_URL}", 500
        return render_template("schedule/job_details.html", job=job)
