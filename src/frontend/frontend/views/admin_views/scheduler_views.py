from typing import Any

from flask import render_template, request
from flask.views import MethodView
from models.admin import Job
from models.task import Task

from frontend.auth import auth_required
from frontend.config import Config
from frontend.core_api import CoreApi
from frontend.data_persistence import DataPersistenceLayer
from frontend.utils.router_helpers import is_htmx_request
from frontend.views.admin_views.admin_mixin import AdminMixin
from frontend.views.base_view import BaseView


def _notification_error(message: str, status_code: int = 500) -> tuple[str, int]:
    notification = BaseView.get_notification_from_dict({"message": message, "error": True})
    return render_template("notification/index.html", notification=notification), status_code


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

    @staticmethod
    def _get_dashboard_data() -> dict[str, Any]:
        dashboard_data = CoreApi().api_get("/config/workers/dashboard")
        return dashboard_data if isinstance(dashboard_data, dict) else {}

    @classmethod
    def _resolve_tab(cls, initial_tab: str | None) -> str:
        tab = (request.args.get("tab") or initial_tab or "scheduled").lower()
        match tab:
            case "scheduled" | "active" | "failed" | "history":
                return tab
            case _:
                return "scheduled"

    def get(self, initial_tab: str | None = None, **kwargs) -> tuple[str, int]:
        """Render the main scheduler dashboard"""
        try:
            selected_tab = self._resolve_tab(initial_tab)
            dashboard_data = self._get_dashboard_data()

            jobs_data = dashboard_data.get("scheduled_jobs")
            jobs = jobs_data if isinstance(jobs_data, list) else []
            jobs.sort(key=lambda job: (job.get("next_run_time") is None, job.get("next_run_time") or ""))

            queues = dashboard_data.get("queues", [])
            if not isinstance(queues, list):
                queues = []

            worker_stats_data = dashboard_data.get("worker_stats")
            worker_stats = worker_stats_data if isinstance(worker_stats_data, dict) else None

            # Get task execution stats
            task_results = DataPersistenceLayer().get_objects(Task)
            stats_meta = getattr(task_results, "extra", {}) if task_results is not None else {}
            task_stats = stats_meta.get("task_stats", {})
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


class ScheduleJobsAPI(MethodView):
    """HTMX endpoint for scheduled jobs table"""

    @auth_required()
    def get(self):
        if not is_htmx_request():
            return SchedulerView().get(initial_tab="scheduled")
        try:
            dashboard_data = SchedulerView._get_dashboard_data()
            jobs_data = dashboard_data.get("scheduled_jobs")
            jobs = jobs_data if isinstance(jobs_data, list) else []
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
            dashboard_data = SchedulerView._get_dashboard_data()
            queues_data = dashboard_data.get("queues")
            queues = queues_data if isinstance(queues_data, list) else []

            worker_stats_data = dashboard_data.get("worker_stats")
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
            dashboard_data = SchedulerView._get_dashboard_data()
            active_jobs_data = dashboard_data.get("active_jobs")
            active_jobs = active_jobs_data if isinstance(active_jobs_data, list) else []
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
            dashboard_data = SchedulerView._get_dashboard_data()
            failed_jobs_data = dashboard_data.get("failed_jobs")
            failed_jobs = failed_jobs_data if isinstance(failed_jobs_data, list) else []
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

            task_stats = dict(
                sorted(
                    raw_task_stats.items(),
                    key=lambda item: item[1].get("last_run") or "",
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


class ScheduleJobDetailsAPI(MethodView):
    @auth_required()
    def get(self, job_id: str):
        job = DataPersistenceLayer().get_object(Job, job_id)
        if job is None:
            return f"Failed to fetch job from: {Config.TARANIS_CORE_URL}", 500
        return render_template("schedule/job_details.html", job=job)
