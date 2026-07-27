from typing import Any

from flask import render_template, request
from flask.typing import ResponseReturnValue
from flask.views import MethodView
from models.admin import ActiveJob, FailedJob, Job, QueueStatus, SchedulerDashboardData, WorkerStats
from models.task import TaskHistoryResponse
from werkzeug.exceptions import HTTPException

from frontend.auth import auth_required
from frontend.cache_models import CacheObject, PagingData
from frontend.config import Config
from frontend.data_persistence import DataPersistenceLayer
from frontend.utils.router_helpers import is_htmx_request, parse_paging_data
from frontend.views.admin_views.admin_base_view import AdminBaseView
from frontend.views.base_view import BaseView


def _paging_data(default_order: str) -> PagingData:
    paging_data = parse_paging_data()
    if paging_data.order:
        return paging_data
    query_params = dict(paging_data.query_params or {})
    query_params["order"] = default_order
    return paging_data.model_copy(update={"order": default_order, "query_params": query_params})


def _dashboard_page(items: list, total_count: int) -> CacheObject:
    return CacheObject(items[:20], total_count=total_count, page=1, limit=20)


def _task_stats_page(task_history: TaskHistoryResponse) -> CacheObject:
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
    if search := (request.args.get("search") or "").strip().lower():
        rows = [row for row in rows if any(search in str(row.get(field) or "").lower() for field in ("id", "task", "worker_id"))]

    order = request.args.get("order", "last_run_desc")
    field, separator, direction = order.rpartition("_")
    if not separator or field not in {"task", "last_run", "last_success", "successes", "failures", "success_pct"}:
        field, direction = "last_run", "desc"
    rows.sort(key=lambda row: str(row.get(field) or "").lower(), reverse=direction == "desc")
    rows.sort(key=lambda row: row.get(field) is None)

    page = max(request.args.get("page", default=1, type=int) or 1, 1)
    limit = max(request.args.get("limit", default=20, type=int) or 20, 1)
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

    @staticmethod
    def _get_dashboard_data() -> SchedulerDashboardData | None:
        return DataPersistenceLayer().get_object(SchedulerDashboardData)

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
            dashboard_data = self._get_dashboard_data()
            if dashboard_data is None:
                raise ValueError("Failed to load scheduler dashboard data")

            history = DataPersistenceLayer().get_object(TaskHistoryResponse)
            if history is None:
                raise ValueError("Failed to load scheduler execution history")

            context = self._common_context()
            context.update(
                {
                    "jobs": _dashboard_page(
                        sorted(
                            dashboard_data.scheduled_jobs,
                            key=lambda job: (job.next_run_time is None, job.next_run_time or ""),
                        ),
                        dashboard_data.scheduled_total_count,
                    ),
                    "queues": dashboard_data.queues,
                    "worker_stats": dashboard_data.worker_stats,
                    "active_jobs": _dashboard_page(
                        sorted(dashboard_data.active_jobs, key=lambda job: (job.started_at is None, job.started_at or "")),
                        dashboard_data.active_total_count,
                    ),
                    "failed_jobs": _dashboard_page(
                        sorted(
                            dashboard_data.failed_jobs,
                            key=lambda job: (job.failed_at is None, job.failed_at or ""),
                            reverse=True,
                        ),
                        dashboard_data.failed_total_count,
                    ),
                    "task_stats": _task_stats_page(history),
                    "total_successes": history.totals.successes,
                    "total_failures": history.totals.failures,
                    "overall_success_rate": history.totals.overall_success_rate,
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
            jobs = DataPersistenceLayer().get_objects(Job, _paging_data("next_run_time_asc"))
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
            active_jobs = DataPersistenceLayer().get_objects(ActiveJob, _paging_data("started_at_asc"))
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
            failed_jobs = DataPersistenceLayer().get_objects(FailedJob, _paging_data("failed_at_desc"))
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
