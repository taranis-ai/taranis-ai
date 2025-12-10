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
            task_stats = {}
            total_successes = 0
            total_failures = 0

            if task_results:
                for task in task_results:
                    if task.task and task.status:
                        if task.task not in task_stats:
                            task_stats[task.task] = {"successes": 0, "failures": 0, "total": 0}

                        if task.status == "SUCCESS":
                            task_stats[task.task]["successes"] += 1
                            total_successes += 1
                        elif task.status == "FAILURE":
                            task_stats[task.task]["failures"] += 1
                            total_failures += 1

                        task_stats[task.task]["total"] = (
                            task_stats[task.task]["successes"] + task_stats[task.task]["failures"]
                        )

                        total = task_stats[task.task]["total"]
                        task_stats[task.task]["success_pct"] = (
                            int((task_stats[task.task]["successes"] * 100) / total) if total > 0 else 0
                        )

            overall_total = total_successes + total_failures
            overall_success_rate = int((total_successes * 100) / overall_total) if overall_total > 0 else 0

            # Get base context with sidebar and admin layout
            context = self._common_context()
            context.update({
                "jobs": jobs,
                "queues": queues,
                "worker_stats": worker_stats,
                "task_results": task_results,
                "task_stats": task_stats,
                "total_successes": total_successes,
                "total_failures": total_failures,
                "overall_success_rate": overall_success_rate,
                "initial_tab": selected_tab,
            })

            return render_template("schedule/dashboard.html", **context), 200

        except Exception as e:
            from frontend.log import logger
            logger.exception(f"Failed to load scheduler dashboard: {e}")
            return render_template("errors/500.html", error=str(e)), 500
