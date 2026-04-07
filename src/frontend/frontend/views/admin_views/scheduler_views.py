from flask import render_template, request
from flask.views import MethodView
from models.admin import ActiveJob, FailedJob, Job, QueueStatus, SchedulerDashboardData, TaskHistoryResponse, WorkerStats

from frontend.auth import auth_required
from frontend.config import Config
from frontend.data_persistence import DataPersistenceLayer
from frontend.utils.router_helpers import is_htmx_request
from frontend.views.admin_views.admin_mixin import AdminMixin
from frontend.views.base_view import BaseView


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

    def get(self, initial_tab: str | None = None, **kwargs) -> tuple[str, int]:
        """Render the main scheduler dashboard"""
        try:
            selected_tab = self._resolve_tab(initial_tab)
            dashboard_data = self._get_dashboard_data()
            if dashboard_data is None:
                raise ValueError("Failed to load scheduler dashboard data")

            jobs = list(dashboard_data.scheduled_jobs)
            jobs.sort(key=lambda job: (job.next_run_time is None, job.next_run_time or ""))

            history = DataPersistenceLayer().get_object(TaskHistoryResponse)
            if history is None:
                raise ValueError("Failed to load scheduler execution history")

            # Get base context with sidebar and admin layout
            context = self._common_context()
            context.update(
                {
                    "jobs": jobs,
                    "queues": dashboard_data.queues,
                    "worker_stats": dashboard_data.worker_stats,
                    "task_results": history.items,
                    "task_stats": history.task_stats,
                    "total_successes": history.totals.successes,
                    "total_failures": history.totals.failures,
                    "overall_success_rate": history.totals.overall_success_rate,
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
            jobs = DataPersistenceLayer().get_objects(Job)
            jobs.sort(key=lambda job: (job.next_run_time is None, job.next_run_time or ""))
            return render_template("schedule/jobs_table.html", jobs=jobs)
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
        except Exception as exc:  # pragma: no cover - defensive rendering path
            return BaseView.render_response_notification({"error": f"Failed to load queues: {exc}"}), 500


class ScheduleActiveJobsAPI(MethodView):
    """HTMX endpoint for active jobs"""

    @auth_required()
    def get(self):
        if not is_htmx_request():
            return SchedulerView().get(initial_tab="active")
        try:
            active_jobs = DataPersistenceLayer().get_objects(ActiveJob)
            active_jobs.sort(key=lambda job: job.started_at or "")
            return render_template("schedule/active_jobs.html", active_jobs=active_jobs)
        except Exception as exc:  # pragma: no cover - defensive rendering path
            return BaseView.render_response_notification({"error": f"Failed to load active jobs: {exc}"}), 500


class ScheduleFailedJobsAPI(MethodView):
    """HTMX endpoint for failed jobs"""

    @auth_required()
    def get(self):
        if not is_htmx_request():
            return SchedulerView().get(initial_tab="failed")
        try:
            failed_jobs = DataPersistenceLayer().get_objects(FailedJob)
            failed_jobs.sort(key=lambda job: job.failed_at or "", reverse=True)
            return render_template("schedule/failed_jobs.html", failed_jobs=failed_jobs)
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

            task_stats = dict(
                sorted(
                    task_history.task_stats.items(),
                    key=lambda item: item[1].last_run or "",
                    reverse=True,
                )
            )

            return render_template(
                "schedule/execution_history.html",
                task_results=task_history.items,
                task_stats=task_stats,
                total_successes=task_history.totals.successes,
                total_failures=task_history.totals.failures,
                overall_success_rate=task_history.totals.overall_success_rate,
            )
        except Exception as exc:  # pragma: no cover - defensive rendering path
            return BaseView.render_response_notification({"error": f"Failed to load history: {exc}"}), 500


class ScheduleJobDetailsAPI(MethodView):
    @auth_required()
    def get(self, job_id: str):
        job = DataPersistenceLayer().get_object(Job, job_id)
        if job is None:
            return f"Failed to fetch job from: {Config.TARANIS_CORE_URL}", 500
        return render_template("schedule/job_details.html", job=job)
