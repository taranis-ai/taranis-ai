from typing import Any

from flask import render_template, request
from flask.typing import ResponseReturnValue
from flask.views import MethodView
from models.admin import ActiveJob, FailedJob, Job, QueueStatus, WorkerStats
from models.task import TaskHistoryResponse
from werkzeug.exceptions import HTTPException

from frontend.auth import auth_required
from frontend.cache_models import CacheObject
from frontend.config import Config
from frontend.data_persistence import DataPersistenceLayer
from frontend.utils.router_helpers import is_htmx_request, parse_paging_data
from frontend.views.admin_views.admin_base_view import AdminBaseView
from frontend.views.base_view import BaseView


def _task_stats_page(task_history: TaskHistoryResponse) -> CacheObject:
    paging_data = parse_paging_data()
    rows = [
        {
            "id": task_id,
            "task": stats.worker_type or task_id,
            "worker_id": stats.worker_id or "unknown",
            "status_badge": stats.status_badge,
            "last_run": stats.last_run,
            "last_success": stats.last_success,
            "successes": stats.successes,
            "failures": stats.failures,
            "success_pct": stats.success_pct,
        }
        for task_id, stats in task_history.task_stats.items()
    ]
    if search := (paging_data.search or "").strip().lower():
        rows = [row for row in rows if any(search in str(row.get(field) or "").lower() for field in ("id", "task", "worker_id"))]

    order = paging_data.order or "last_run_desc"
    field, separator, direction = order.rpartition("_")
    if (
        not separator
        or field not in {"task", "last_run", "last_success", "successes", "failures", "success_pct"}
        or direction not in {"asc", "desc"}
    ):
        field, direction = "last_run", "desc"
    order = f"{field}_{direction}"
    if field in {"successes", "failures", "success_pct"}:
        rows.sort(key=lambda row: row.get(field) or 0, reverse=direction == "desc")
    else:
        rows.sort(key=lambda row: str(row.get(field) or "").lower(), reverse=direction == "desc")
    rows.sort(key=lambda row: row.get(field) is None)

    page = paging_data.page if paging_data.page and paging_data.page > 0 else 1
    limit = paging_data.limit if paging_data.limit and paging_data.limit > 0 else 20
    offset = (page - 1) * limit
    return CacheObject(rows[offset : offset + limit], total_count=len(rows), page=page, limit=limit, order=order)


class SchedulerView(AdminBaseView):
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
        tab = (request.args.get("tab") or initial_tab or "scheduled").lower()
        match tab:
            case "scheduled" | "active" | "failed" | "history":
                return tab
            case _:
                return "scheduled"

    def get(self, initial_tab: str | None = None, **kwargs: Any) -> ResponseReturnValue:
        """Render the main scheduler dashboard"""
        try:
            selected_tab = self._resolve_tab(initial_tab)
            persistence = DataPersistenceLayer()
            queues = persistence.get_objects(QueueStatus)
            worker_stats = persistence.get_object(WorkerStats)
            jobs = active_jobs = failed_jobs = task_stats = None
            total_successes = total_failures = overall_success_rate = 0

            paging_data = parse_paging_data()
            match selected_tab:
                case "scheduled":
                    jobs = persistence.get_objects(Job, paging_data)
                case "active":
                    active_jobs = persistence.get_objects(ActiveJob, paging_data)
                case "failed":
                    failed_jobs = persistence.get_objects(FailedJob, paging_data)
                case "history":
                    history = persistence.get_object(TaskHistoryResponse)
                    if history is None:
                        raise ValueError("Failed to load scheduler execution history")
                    task_stats = _task_stats_page(history)
                    total_successes = history.totals.successes
                    total_failures = history.totals.failures
                    overall_success_rate = history.totals.overall_success_rate

            context = self._common_context()
            context.update(
                {
                    "jobs": jobs,
                    "queues": queues,
                    "worker_stats": worker_stats,
                    "active_jobs": active_jobs,
                    "failed_jobs": failed_jobs,
                    "task_stats": task_stats,
                    "total_successes": total_successes,
                    "total_failures": total_failures,
                    "overall_success_rate": overall_success_rate,
                    "initial_tab": selected_tab,
                }
            )

            return render_template("schedule/dashboard.html", **context), 200

        except HTTPException:
            raise
        except Exception as e:
            from frontend.log import logger

            logger.exception(f"Failed to load scheduler dashboard: {e}")
            return render_template("errors/500.html", error=str(e)), 500


class ScheduleJobsAPI(MethodView):
    """HTMX endpoint for scheduled jobs table"""

    @auth_required()
    def get(self):
        if not is_htmx_request():
            return SchedulerView().get(initial_tab="scheduled")
        try:
            jobs = DataPersistenceLayer().get_objects(Job, parse_paging_data())
            return render_template("schedule/jobs_table.html", jobs=jobs)
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - defensive rendering path
            return BaseView.render_response_notification({"error": f"Failed to load jobs: {exc}"}), 500


class ScheduleQueuesAPI(MethodView):
    """HTMX endpoint for queue status cards"""

    @auth_required()
    def get(self):
        if not is_htmx_request():
            return SchedulerView().get(initial_tab="scheduled")
        try:
            persistence = DataPersistenceLayer()
            queues = persistence.get_objects(QueueStatus)
            worker_stats = persistence.get_object(WorkerStats)
            return render_template("schedule/queue_cards.html", queues=queues, worker_stats=worker_stats)
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - defensive rendering path
            return BaseView.render_response_notification({"error": f"Failed to load queues: {exc}"}), 500


class ScheduleActiveJobsAPI(MethodView):
    """HTMX endpoint for active jobs"""

    @auth_required()
    def get(self):
        if not is_htmx_request():
            return SchedulerView().get(initial_tab="active")
        try:
            active_jobs = DataPersistenceLayer().get_objects(ActiveJob, parse_paging_data())
            return render_template("schedule/active_jobs.html", active_jobs=active_jobs)
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - defensive rendering path
            return BaseView.render_response_notification({"error": f"Failed to load active jobs: {exc}"}), 500


class ScheduleFailedJobsAPI(MethodView):
    """HTMX endpoint for failed jobs"""

    @auth_required()
    def get(self):
        if not is_htmx_request():
            return SchedulerView().get(initial_tab="failed")
        try:
            failed_jobs = DataPersistenceLayer().get_objects(FailedJob, parse_paging_data())
            return render_template("schedule/failed_jobs.html", failed_jobs=failed_jobs)
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - defensive rendering path
            return BaseView.render_response_notification({"error": f"Failed to load failed jobs: {exc}"}), 500


class ScheduleHistoryAPI(MethodView):
    """HTMX endpoint for execution history"""

    @auth_required()
    def get(self):
        if not is_htmx_request():
            return SchedulerView().get(initial_tab="history")
        try:
            task_history = DataPersistenceLayer().get_object(TaskHistoryResponse)
            if task_history is None:
                raise ValueError("Failed to load task history")

            return render_template(
                "schedule/execution_history.html",
                task_stats=_task_stats_page(task_history),
                total_successes=task_history.totals.successes,
                total_failures=task_history.totals.failures,
                overall_success_rate=task_history.totals.overall_success_rate,
            )
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - defensive rendering path
            return BaseView.render_response_notification({"error": f"Failed to load history: {exc}"}), 500


class ScheduleJobDetailsAPI(MethodView):
    @auth_required()
    def get(self, job_id: str):
        job = DataPersistenceLayer().get_object(Job, job_id)
        if job is None:
            return f"Failed to fetch job from: {Config.TARANIS_CORE_URL}", 500
        return render_template("schedule/job_details.html", job=job)
