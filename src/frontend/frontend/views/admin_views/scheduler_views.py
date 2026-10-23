from typing import Any

from flask import render_template, request
from flask.typing import ResponseReturnValue
from models.admin import ActiveJob, FailedJob, Job, QueueStatus, WorkerStats
from models.task import TaskHistoryResponse, TaskRun, TaskRunFilter
from werkzeug.exceptions import HTTPException

from frontend.cache_models import CacheObject
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.utils.router_helpers import is_htmx_request, parse_paging_data
from frontend.views.admin_views.admin_base_view import AdminBaseView


def _task_stats_page(task_history: TaskHistoryResponse) -> CacheObject:
    paging_data = parse_paging_data()
    rows: list[dict[str, Any]] = [
        {
            "id": task_id,
            "task": stats.worker_type or task_id,
            "worker_id": stats.worker_id or "unknown",
            "status_badge": stats.status_badge,
            "last_run": stats.last_run,
            "last_success": stats.last_success,
            "successes": stats.successes,
            "warnings": stats.warnings,
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


def _completed_runs_page() -> CacheObject:
    filters = TaskRunFilter.model_validate(request.args.to_dict())
    paging = parse_paging_data().model_copy(
        update={
            "page": filters.page,
            "limit": filters.limit,
            "order": filters.order,
            "search": filters.search,
            "query_params": {**{key: str(value) for key, value in filters.model_dump(exclude_none=True).items()}, "tab": "completed"},
        }
    )
    return DataPersistenceLayer().get_objects(TaskRun, paging, use_cache=False)


class SchedulerView(AdminBaseView):
    model = Job
    icon = "calendar-days"
    htmx_list_template = "schedule/dashboard.html"
    htmx_update_template = "schedule/dashboard.html"
    default_template = "schedule/dashboard.html"
    base_route = "admin.scheduler"
    _read_only = True
    _index = 61

    @classmethod
    def _resolve_tab(cls, initial_tab: str | None) -> str:
        tab = (request.args.get("tab") or initial_tab or "scheduled").lower()
        match tab:
            case "scheduled" | "active" | "completed" | "failed" | "history":
                return tab
            case _:
                return "scheduled"

    def get(self, initial_tab: str | None = None, **kwargs: Any) -> ResponseReturnValue:
        """Read current scheduler state without waiting for list-cache expiry."""
        try:
            selected_tab = self._resolve_tab(initial_tab)
            persistence = DataPersistenceLayer()
            partial = is_htmx_request()
            queues = persistence.get_objects(QueueStatus, use_cache=False) if not partial else None
            worker_stats = persistence.get_object(WorkerStats, use_cache=False) if not partial else None
            jobs = active_jobs = failed_jobs = task_stats = completed_runs = None
            total_successes = total_warnings = total_failures = overall_success_rate = 0

            paging_data = parse_paging_data()
            match selected_tab:
                case "scheduled":
                    jobs = persistence.get_objects(Job, paging_data, use_cache=False)
                case "active":
                    active_jobs = persistence.get_objects(ActiveJob, paging_data, use_cache=False)
                case "completed":
                    completed_runs = _completed_runs_page()
                case "failed":
                    failed_jobs = persistence.get_objects(FailedJob, paging_data, use_cache=False)
                case "history":
                    history = persistence.get_object(TaskHistoryResponse, use_cache=False)
                    if history is None:
                        raise ValueError("Failed to load scheduler execution history")
                    task_stats = _task_stats_page(history)
                    total_successes = history.totals.successes
                    total_warnings = history.totals.warnings
                    total_failures = history.totals.failures
                    overall_success_rate = history.totals.overall_success_rate

            context = {} if partial else self._common_context()
            context.update(
                {
                    "jobs": jobs,
                    "queues": queues,
                    "worker_stats": worker_stats,
                    "active_jobs": active_jobs,
                    "completed_runs": completed_runs,
                    "failed_jobs": failed_jobs,
                    "task_stats": task_stats,
                    "total_successes": total_successes,
                    "total_warnings": total_warnings,
                    "total_failures": total_failures,
                    "overall_success_rate": overall_success_rate,
                    "initial_tab": selected_tab,
                }
            )

            return render_template("schedule/content.html" if partial else "schedule/dashboard.html", **context), 200

        except HTTPException:
            raise
        except Exception:
            logger.exception("Failed to load scheduler dashboard")
            if is_htmx_request():
                return self.render_response_notification({"error": "Failed to load scheduler dashboard."}), 500
            return render_template("errors/500.html", error="Failed to load scheduler dashboard."), 500


class ScheduleQueuesAPI(AdminBaseView):
    """HTMX endpoint for queue status cards"""

    def get(self, **kwargs: Any) -> ResponseReturnValue:
        if not is_htmx_request():
            return SchedulerView().get(initial_tab="scheduled")
        try:
            persistence = DataPersistenceLayer()
            queues = persistence.get_objects(QueueStatus, use_cache=False)
            worker_stats = persistence.get_object(WorkerStats, use_cache=False)
            return render_template("schedule/queue_cards.html", queues=queues, worker_stats=worker_stats)
        except HTTPException:
            raise
        except Exception:  # pragma: no cover - defensive rendering path
            logger.exception("Failed to load queues")
            return self.render_response_notification({"error": "Failed to load queues."}), 500
